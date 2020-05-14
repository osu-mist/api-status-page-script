import json
import sys
import requests


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

    # Should we update incident status to resolved if test succeeds on API
    # with open issue?
    def updateStatuses(self):
        print('Updating statuses')


if __name__ == '__main__':
    status_page = StatusPage()
    status_page.getAllStatuses()
    status_page.getAllIncidents()
