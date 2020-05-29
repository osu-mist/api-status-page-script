import argparse
import json
import sys
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException


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
        args = parser.parse_known_args()[0]
        self.session = requests.Session()
        self.config_json = json.load(open(args.config_path))
        self.api_status_json = json.load(open(args.api_status_path))
        self.access_token = self.config_json['access_token']
        self.base_url = self.config_json['base_url']
        self.api_map = self.config_json['api_map']
        self.session.headers = {'x-cachet-token': self.access_token}
        self.open_incidents = []
        self.timed_out = []

    def get_all_open_incidents(self):
        """Fetches all incidents not marked as 'Resolved'"""
        self.open_incidents = []
        try:
            response = self.session.get(f'{self.base_url}/incidents')
        except RequestException as err:
            sys.exit(f'REQUEST ERROR! Unable to get incidents.\n{err}')
        for incident in response.json()['data']:
            if incident['status'] != 4:
                self.open_incidents.append(incident)

    def parse_tests(self, passed):
        """
        Parses through a set of passed or failed tests. If the tests passed,
        resolve any open incidents with a passed test. If the tests failed,
        create new incidents for each failed test if not already open.
        """
        pass_or_fail = 'passed_tests' if passed else 'failed_tests'
        for test_case in self.api_status_json[pass_or_fail]:
            api_map = self.api_map
            already_reported = False
            parsed_url = urlparse(test_case['base_url'])
            split_path = parsed_url.path.split('/')
            api_version = split_path[1]
            api_name = split_path[2]
            version_and_name = f'{api_version}/{api_name}'
            incident_id = None

            if version_and_name in api_map:
                component_id = api_map[version_and_name]
                for incident in self.open_incidents:
                    if test_case['base_url'] == incident['name']:
                        already_reported = True
                        incident_id = incident['id']
                if passed and already_reported:
                    body = {
                        'status': 4,
                        'component_id': component_id,
                        'component_status': 1
                    }
                    try:
                        self.session.put(
                            f'{self.base_url}/incidents/{incident_id}',
                            data=body
                        )
                        print(
                            f'Updated incident status of '
                            f'"{test_case["base_url"]}" to {body["status"]}'
                        )
                    except RequestException as err:
                        sys.exit(
                            f'REQUEST ERROR! Unable to update incident.\n{err}'
                        )
                elif not passed and not already_reported:
                    message = (
                        f'An issue has been reported with {api_name} api '
                        f'{api_version}. Failed test url: '
                        f'{test_case["base_url"]}'
                    )
                    # Mark 'Performance Issues' if gateway timeout,
                    # otherwise mark as 'Minor Outage'
                    c_status = 3
                    if test_case['response_code'] == 504:
                        c_status = 2
                        self.timed_out.append(component_id)
                    body = {
                        'name': test_case['base_url'],
                        'message': message,
                        'status': 1,
                        'visible': 1,
                        'component_id': component_id,
                        'component_status': c_status,
                    }
                    try:
                        self.session.post(
                            f'{self.base_url}/incidents',
                            data=body
                        )
                    except RequestException as err:
                        sys.exit(
                            f'REQUEST ERROR! Incident not posted:\n{err}')
                    print(
                        f'Posted new incident with endpoint = '
                        f'"{test_case["base_url"]}"'
                    )

    def update_component_status(self):
        """Mark all components with open incidents with the appropriate status
        value"""
        for incident in self.open_incidents:
            c_id = incident['component_id']
            body = {'status': 2 if c_id in self.timed_out else 3}
            try:
                self.session.put(
                    f'{self.base_url}/components/{c_id}',
                    data=body
                )
                print(
                    f'Updated status of component {c_id} to {body["status"]}'
                )
            except RequestException as err:
                sys.exit(
                    f'REQUEST ERROR! Unable to update component status.\n{err}'
                )


if __name__ == '__main__':
    status_page = StatusPage()

    # get incidents, parse failing tests, then parse passing tests
    status_page.get_all_open_incidents()
    status_page.parse_tests(False)
    status_page.parse_tests(True)

    # get open incidents again after they were updated, then update api status
    status_page.get_all_open_incidents()
    status_page.update_component_status()
