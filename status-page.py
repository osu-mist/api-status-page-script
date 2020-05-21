import argparse
import json
import sys
from urllib.parse import urlparse

import requests


class StatusPage:
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--config',
            dest='config_path',
            help='Path to configuration.json',
            required=True
        )
        parser.add_argument(
            '--status',
            dest='api_status_path',
            help='Path to api_status.json',
            required=True
        )
        args, unknown_args = parser.parse_known_args()
        self.config_json = json.load(open(args.config_path))
        self.api_status_json = json.load(open(args.api_status_path))
        self.access_token = self.config_json['access_token']
        self.base_url = self.config_json['base_url']
        self.api_map = self.config_json['api_map']
        self.header = {'x-cachet-token': self.access_token}
        self.broken_components = []
        self.open_incidents = []

    def get_broken_components(self):
        """Fetches all apis not marked as 'Operational'"""
        try:
            response = requests.get(f'{self.base_url}/components', self.header)
        except requests.exceptions.RequestException as err:
            print(f'REQUEST ERROR! Unable to get components.\n{err}')
            sys.exit(1)
        for component in response.json()['data']:
            if component['status'] != 1:
                self.broken_components.append(component)

    def get_all_open_incidents(self):
        """Fetches all incidents not marked as 'Resolved'"""
        try:
            response = requests.get(f'{self.base_url}/incidents', self.header)
        except requests.exceptions.RequestException as err:
            print(f'REQUEST ERROR! Unable to get incidents.\n{err}')
            sys.exit(1)
        for incident in response.json()['data']:
            status = incident['status']
            if status != 4:
                self.open_incidents.append(incident)

    def update_incident_status(self):
        """Goes through all passed and failed tests, resolves open incidents with a passed test, and creates new
        incidents for failed tests."""
        api_map = self.api_map

        # If there are any test failures, open an incident if there is none open already
        for failed_test in self.api_status_json['failed_tests']:
            already_reported = False
            parsed_url = urlparse(failed_test['base_url'])
            split_path = parsed_url.path.split('/')
            api_version = split_path[1]
            api_name = split_path[2]
            version_and_name = f'{api_version}/{api_name}'

            if version_and_name in api_map:
                component_id = api_map[version_and_name]
                for incident in self.open_incidents:
                    if component_id == incident['component_id']:
                        already_reported = True
                if not already_reported:
                    body = {
                        'name': failed_test['base_url'],
                        'message': f'Jenkins has reported an issue with {api_name} api {api_version}.\
                                     Failed test url: {failed_test["base_url"]}',
                        'status': 1,
                        'visible': 1,
                        'component_id': component_id,
                        'component_status': 2,

                    }
                    try:
                        response = requests.post(f'{self.base_url}/incidents', headers=self.header, data=body)
                    except requests.exceptions.RequestException as err:
                        print(f'REQUEST ERROR! Incident not posted:\n{err}')
                        sys.exit(1)
                    print(f'Posted New Incident: {response}')

        # then parse through passed tests and resolve any previously opened incidents if it shares the same endpoint
        for passed_test in self.api_status_json['passed_tests']:
            already_reported = False
            parsed_url = urlparse(passed_test['base_url'])
            split_path = parsed_url.path.split('/')
            api_version = split_path[1]
            api_name = split_path[2]
            version_and_name = f'{api_version}/{api_name}'
            incident_id = None

            if version_and_name in api_map:
                component_id = api_map[version_and_name]
                for incident in self.open_incidents:
                    if component_id == incident['component_id'] \
                            and passed_test['base_url'] == incident['name']:
                        already_reported = True
                        incident_id = incident['id']

                if already_reported:
                    body = {
                        'status': 4,
                        'component_id': component_id,
                        'component_status': 1
                    }
                    try:
                        response = requests.put(
                            f'{self.base_url}/incidents/{incident_id}',
                            headers=self.header,
                            data=body
                        )
                    except requests.exceptions.RequestException as err:
                        print(f'REQUEST ERROR! Unable to update incident.\n{err}')
                        sys.exit(1)
                    print(f'Updated Incident Status: {response}')

    def update_component_status(self):
        """Mark all components with open incidents with 'Performance Issues' status """
        for broken_api in self.broken_components:
            for open_incident in self.open_incidents:
                if open_incident['component_id'] == broken_api['id']:
                    body = {'status': 2}
                    try:
                        requests.put(f'{self.base_url}/components/{broken_api["id"]}', headers=self.header, data=body)
                    except requests.exceptions.RequestException as err:
                        print(f'REQUEST ERROR! Unable to update component status.\n{err}')
                        sys.exit(1)
                    break


if __name__ == '__main__':
    status_page = StatusPage()

    # get incidents, then create/update them
    status_page.get_all_open_incidents()
    status_page.update_incident_status()

    # get open incidents again after they are updated
    status_page.get_all_open_incidents()

    # get all apis with reported issues and reassign status based on if there's any open incidents
    status_page.get_broken_components()
    status_page.update_component_status()
