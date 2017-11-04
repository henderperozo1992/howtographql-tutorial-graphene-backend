# howtographql-graphene-tutorial-fixed -- links/schema.py
#
# Copyright © 2017 Sean Bolton.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import graphene
from graphene import ObjectType, relay
from graphene.relay import Node
from graphene_django import DjangoObjectType

from links.models import LinkModel
from users.schema import get_user_from_auth_token


class Link(DjangoObjectType):
    class Meta:
        model = LinkModel
        interfaces = (Node, )
        # We are going to provide a custom Connection, so we need to tell graphene-django not to
        # create one. Failing to do this will result in a error like "AssertionError: Found
        # different types with the same name in the schema: LinkConnection, LinkConnection."
        use_connection = False


class LinkOrderBy(graphene.Enum):
    """This provides the schema's LinkOrderBy Enum type, for ordering LinkConnection."""
    createdAt_DESC = '-created_at'
    createdAt_ASC = 'created_at'
    description_ASC = 'description'
    description_DESC = '-description'
    id_ASC = 'id'
    id_DESC = '-id'
    #updatedAt_ASC = 'updated_at'
    #updatedAt_DESC = '-updated_at'
    url_ASC = 'url'
    url_DESC = '-url'


class LinkConnection(relay.Connection):
    """A custom Connection for queries on Link. Using this instead of DjangoConnectionField or
    DjangoFilterConnectionField solves two problems:
    - django_filters FilterSet can't use custom enums for OrderFilter choices, and
    - DjangoConnectionField in graphene-django 2.0 can no longer be given a custom Connection,
        which makes it difficult to add custom fields (such as the ubiquitous 'totalCount') on the
        connection without monkey-patching.
    """

    # total_count = graphene.Int()  -- a custom field on the connection, to be added later

    class Meta:
        node = Link

    @staticmethod
    def get_input_fields():
        return {
            'order_by': graphene.Argument(LinkOrderBy) # an input field using the custon enum
        }

    def resolve_all_links(self, info, **args):
        qs = LinkModel.objects.all()
        order_by = args.get('order_by')
        if order_by:
            qs = qs.order_by(order_by)
        return qs


class Viewer(ObjectType):
    class Meta:
        interfaces = (Node, )

    all_links = relay.ConnectionField(
        LinkConnection,
        resolver=LinkConnection.resolve_all_links,
        **LinkConnection.get_input_fields()
    )


class Query(object):
    viewer = graphene.Field(Viewer)
    node = Node.Field()

    def resolve_viewer(self, info):
        return not None # none of Viewer's resolvers need Viewer()


class CreateLink(relay.ClientIDMutation):
    # mutation CreateLinkMutation($input: CreateLinkInput!) {
    #   createLink(input: $input) {
    #     link {
    #       id
    #       createdAt
    #       url
    #       description
    #     }
    #   }
    # }
    # example variables:
    #   input {
    #       description: "New Link",
    #       url: "http://example.com",
    #       postedById: 1,
    #       clientMutationId: "",
    #   }

    link = graphene.Field(Link, required=True)

    class Input:
        description = graphene.String(required=True)
        url = graphene.String(required=True)
        posted_by_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, url, description, posted_by_id=None,
                               client_mutation_id=None):
        # In order to have this work with early stages of the front-end tutorial, this will allow
        # links to be created without a user auth token or postedById. If a postedById is present,
        # then the auth token must be as well. If both are present, then they must agree.
        user = get_user_from_auth_token(info.context) or None
        if user or posted_by_id:
            if not user:
                raise Exception('Only logged-in users may create links!')
            if posted_by_id:
                try:
                    posted_by_user = Node.get_node_from_global_id(info, posted_by_id)
                    assert posted_by_user.pk == user.pk
                except:
                    raise Exception('postedById does not match user ID!')
        link = LinkModel(
            url=url,
            description=description,
            posted_by=user,
        )
        link.save()

        return CreateLink(link=link)


class Mutation(object):
    create_link = CreateLink.Field()
