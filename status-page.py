import json
import sys
import requests
from urllib.parse import urlparse


class StatusPage:
    def __init__(self):
        config_data_file = open(sys.argv[1])
        log_file = open(sys.argv[2])
        self.config_json = json.load(config_data_file)
        self.log_json = json.load(log_file)
        self.access_token = self.config_json['access_token']
        self.base_url = self.config_json['base_url']
        self.header = {'x-cachet-token': self.access_token}
        self.components = {
            'operational': [],
            'performance_issues': [],
            'partial_outage': [],
            'major_outage': []
        }
        self.incidents = {
            'investigating': [],
            'identified': [],
            'watching': [],
            'fixed': []
        }

    def getAllStatuses(self):
        response = requests.get(f'{self.base_url}/components', self.header)
        for component in response.json()['data']:
            status = component['status']
            if status == 1:
                self.components['operational'].append(component)
            elif status == 2:
                self.components['performance_issues'].append(component)
            elif status == 3:
                self.components['partial_outage'].append(component)
            elif status == 4:
                self.components['major_outage'].append(component)

    def getAllIncidents(self):
        response = requests.get(f'{self.base_url}/incidents', self.header)
        for incident in response.json()['data']:
            status = incident['status']
            if status == 1:
                self.incidents['investigating'].append(incident)
            if status == 2:
                self.incidents['identified'].append(incident)
            if status == 3:
                self.incidents['watching'].append(incident)
            if status == 4:
                self.incidents['fixed'].append(incident)

    def updateStatuses(self):
        component_map = {
            'v1/academic-disciplines': 3,
            'v1/advisors': 4,
            'v1/xeapps': 5,
            'v1/beaverbus': 6,
            'v1/directory': 7,
            'v2/directory': 8,
            'v1/finance': 9,
            'v1/hr': 10,
            'v1/identify': 11,
            'v1/locations': 12,
            'v1/oauth2': 13,
            'v1/onbase': 14,
            'v1/persons': 15,
            'v1/staff-fee-privilege': 16,
            'v1/students': 17,
            'v1/terms': 18,
            'v1/textbooks': 19
        }

        # first, find all open incidents.
        open_incidents = []
        for incident_status in self.incidents:
            if incident_status != 'fixed':
                for incident in self.incidents[incident_status]:
                    open_incidents.append(incident)

        # then, if there are any test failures, open an incident if there is none open already
        for failed_test in self.log_json['failed_tests']:
            already_reported = False
            parsed_url = urlparse(failed_test['base_url'])
            split_path = parsed_url.path.split('/')
            api_version = split_path[1]
            api_name = split_path[2]
            version_and_name = f'{api_version}/{api_name}'
            print(version_and_name)
            for incident in open_incidents:
                if component_map[version_and_name] == incident['component_id']:
                    already_reported = True
            if not already_reported:
                body = {
                    'name': f'Jenkins-reported downtime for {api_name} {api_version}',
                    'message': f'Jenkins has reported an issue with {api_name} api. This issue is under investigation.',
                    'status': 1,
                    'visible': 1,
                    'component_id': component_map[version_and_name],
                    'component_status': 2,
                }
                response = requests.post(f'{self.base_url}/incidents', headers=self.header, data=body)


if __name__ == '__main__':
    status_page = StatusPage()
    status_page.getAllStatuses()
    status_page.getAllIncidents()
    status_page.updateStatuses()
