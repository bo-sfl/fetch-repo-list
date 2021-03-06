import json 
import argparse
from datetime import datetime, timedelta
from functools import partial
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

class Repo(object):
    """Class store repo information"""
    def __init__(self, data):
        self.name = data['nameWithOwner']
        self.last_updated = datetime.fromisoformat(data["pushedAt"][:-1])
        template = data['templateRepository']
        if template:
            self.template =  template['nameWithOwner']
        else:
            self.template = None


def create_client(token):
    """Create a Graph DB query client"""
    headers = {
        "Authorization": f"token {token}", 
    }
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url="https://api.github.com/graphql", headers=headers)

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)
    return client


def generate_query(cursor=None):
    """Construct a Github graph api query"""
    if cursor:
        after = f' after: "{cursor}"'
    else:
        after = ""

    return gql(
        f'''
        {{
            viewer {{
                repositories(first: 100{after}) {{
                    edges {{
                        cursor
                        node {{
                            nameWithOwner
                            pushedAt
                            templateRepository {{
                                nameWithOwner
                            }}
                        }}
                    }}
                }}
            }}
        }}
        '''
    )

def repo_filters(repo, template_name, last_n_day):
    """Filter a repo based on given criteria """
    if repo.template != template_name:
        return False
    if repo.last_updated < datetime.today() - timedelta(days=last_n_day):
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description='Process inputs.')
    parser.add_argument('--last_active', type=int, default=28)
    parser.add_argument(
        '--template_name', 
        type=str, 
        default="SFLScientific/SFL-Template")
    parser.add_argument(
        '--token', 
        type=str, 
        required=True)

    args = parser.parse_args()

    client = create_client(args.token)
    current_cursor = None
    results = []
    while True:
        # Construct a GraphQL query
        query = generate_query(current_cursor)
        # Execute the query on the transport
        result = client.execute(query)['viewer']['repositories']['edges']
        results.extend([Repo(x['node']) for x in result])
        if len(result) < 100:
            break
        else:
            current_cursor = result[-1]['cursor']
    
    repo_filter = partial(
        repo_filters, 
        template_name=args.template_name, 
        last_n_day=args.last_active,
        )

    repo_list =  [x.name for x in filter(repo_filter, results)]
    with open("repos.txt", "w") as f:
        f.write(f'{{\\"repo\\":{repo_list}}}')


if __name__ == "__main__":
    main()