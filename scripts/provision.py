#!/usr/bin/env python
import yaml
import json
import os
import requests
from requests.auth import HTTPBasicAuth
import logging
import urllib3
from attrdict import AttrDict
import glob
import argparse

urllib3.disable_warnings()
logger = logging.getLogger(os.path.basename(__file__))


class L2vpnService(object):

    def __init__(self):

        with open(os.path.join(os.path.dirname(__file__), 'config.yaml')) as fd:
            self.config = AttrDict(yaml.safe_load(fd.read()))

        self.service_dir = os.path.join(os.path.dirname(__file__), '../l2vpn')
        self.existing_customers = {}
        self.service = '{}:{}'.format(self.config.service.path, self.config.service.key)

    def interact_with_nso(self, method='get', uri=None, payload=None):
        auth = HTTPBasicAuth(self.config.nso.username, self.config.nso.password)
        headers = {
            'Accept': 'application/yang-data+json',
            'Content-type': 'application/yang-data+json',
        }

        url = '{}/{}'.format(self.config.nso.host, uri)
        logger.debug('interact_with_nso({}, url={}, payload={}'.format(
            method, uri, payload
        ))
        response = getattr(requests, method.lower())(url, headers=headers,
                                                     auth=auth, verify=False, 
                                                     data=payload)
        if response.status_code == 404:
            return {}
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error('Error during NSO RESTCONF operation: ' + str(e))
            logger.error(response.content)
        return response

    def _get_customer_from_payload(self, payload):
        try:
            return payload[self.service][self.config.service.key]
        except (AttributeError, KeyError):
            return None

    def read_service_file(self, filename):
        '''
        read a yaml config file and returns
        a dict json payload suitable to send towards NSO
        '''
        with open(filename) as fd:
            cust_services = yaml.safe_load(fd.read())

        service_payload = {
            self.service: cust_services
        }
        return(service_payload)

    def _get_dryrun_payload(self, response):
        result = ''
        try:
            d = response.json()
            for elem in d['dryrun-result']['native']['device']:
                result += '\nDevice: {}:\n{}'.format(elem['name'], elem['data'])
        except Exception:
            result = ''
        return result

    def _get_error_payload(self, response):
        result = ''
        try:
            d = response.json()
            for elem in d['errors']['error']['device']:
                result += '\nDevice: {}:\n{}'.format(elem['name'], elem['data'])
        except Exception:
            result = ''
        return result

    def get_provisioned_customers(self):
        '''
        retrieve a list of customers currently provisioned
        '''
        r = self.interact_with_nso(method='get', 
                                   uri='/restconf/data/' + self.service)
        if int(r.status_code / 100) == 2:
            if len(r.content):
                d = r.json()
            else:
                d = {self.service: []}
            
            return [c[self.config.service.key] for c in d[self.service] if self.config.service.key in c]
        else:
            r.raise_for_status()

    def provision_services(self, cust=None, dryrun=True):

        # first remember which customers are currently provisioned so we can
        # handle deletion of the whole customer file
        provisioned_customers = self.get_provisioned_customers()
        logger.debug('provisioned customers: {}'.format(provisioned_customers))

        # process all the customer services found in the repo
        for f in glob.glob('{}/*.yaml'.format(self.service_dir)):
            logger.debug('processing file ' + f)
            service_payload = self.read_service_file(f)

            # send a PUT request for this customer, which takes care of
            # changes, additions and deletions for this customer

            cust = self._get_customer_from_payload(service_payload)
            if cust is None:
                logger.error('Error, no customer service data found in {}'.format(f))
                continue

            msg = 'Provision service for customer "{}"'.format(cust)
            url = 'restconf/data/{}={}'.format(self.service, cust)
            if dryrun:
                url += '?dryrun=native'
                msg += ' (dry run)'
            logger.info(msg)
            response = self.interact_with_nso(method='put', uri=url, payload=json.dumps(service_payload))
            if dryrun:
                logger.info('dryrun for cust {} returned status {}, content: {}'.format(
                    cust, response.status_code, self._get_dryrun_payload(response)
                ))
            else:
                logger.info('PUT restconf operations returned {}/{}'.format(
                    response.ok, response.status_code))

            # note that this customer has been provisioned
            while cust in provisioned_customers:
                provisioned_customers.remove(cust)

        # delete those customers which have not been provisioned earlier
        for cust in provisioned_customers:
            msg = 'Deleting service for customer "{}"'.format(cust)
            url = 'restconf/data/{}={}'.format(self.service, cust)
            if dryrun:
                url += '?dryrun=native'
                msg += ' (dry run)'
            logger.info(msg)

            response = self.interact_with_nso(method='delete', uri=url)
            if dryrun:
                logger.info('dryrun for cust {} returned status {}, content: {}'.format(
                    cust, response.status_code, self._get_dryrun_payload(response)
                ))
            else:
                logger.info('DELETE restconf operations returned {}/{}'.format(
                    response.ok, response.status_code))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provision L2VPN service')
    parser.add_argument('--dryrun', action='store_true', help='only dryrun the operations')
    parser.add_argument('--debug', action='store_true', help='print more debugging output')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    L2vpnService().provision_services(dryrun=args.dryrun)
