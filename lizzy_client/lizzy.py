import json
import time
from typing import Dict, List, Optional

import requests
from clickclick import warning
from urlpath import URL

from .version import VERSION


def make_header(access_token: str):
    headers = dict()
    headers['Authorization'] = 'Bearer {}'.format(access_token)
    headers['Content-type'] = 'application/json'
    return headers


class Lizzy:
    def __init__(self, base_url: str, access_token: str):
        base_url = URL(base_url.rstrip('/'))
        self.api_url = base_url if base_url.path == '/api' else base_url / 'api'
        self.access_token = access_token

    @property
    def stacks_url(self) -> URL:
        return self.api_url / 'stacks'

    def delete(self, stack_id: str):
        url = self.stacks_url / stack_id

        header = make_header(self.access_token)
        request = url.delete(headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()

    def get_stack(self, stack_id: str) -> dict:
        header = make_header(self.access_token)
        url = self.stacks_url / stack_id
        request = url.get(headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json()

    def get_stacks(self, stack_reference: Optional[List[str]]=None) -> list:
        fetch_stacks_url = self.stacks_url
        if stack_reference:
            fetch_stacks_url = fetch_stacks_url.with_query({
                'references': ','.join(stack_reference)
            })

        response = fetch_stacks_url.get(headers=make_header(self.access_token),
                                        verify=False)

        lizzy_version = response.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))

        response.raise_for_status()
        return response.json()

    def new_stack(self,
                  image_version: str,
                  keep_stacks: int,
                  new_traffic: int,
                  senza_yaml_path: str,
                  stack_version: Optional[str],
                  disable_rollback: bool,
                  parameters: List[str]) -> Dict[str, str]:
        """
        Requests a new stack.
        """
        header = make_header(self.access_token)

        with open(senza_yaml_path) as senza_yaml_file:
            senza_yaml = senza_yaml_file.read()

        data = {'image_version': image_version,
                'disable_rollback': disable_rollback,
                'keep_stacks': keep_stacks,
                'new_traffic': new_traffic,
                'parameters': parameters,
                'senza_yaml': senza_yaml}

        if stack_version:
            data['stack_version'] = stack_version

        request = self.stacks_url.post(data=json.dumps(data, sort_keys=True), headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        request.raise_for_status()
        return request.json()

    def traffic(self, stack_id: str, percentage: int):
        url = self.stacks_url / stack_id
        data = {"new_traffic": percentage}

        header = make_header(self.access_token)
        request = url.patch(data=json.dumps(data), headers=header, verify=False)
        lizzy_version = request.headers.get('X-Lizzy-Version')
        if lizzy_version and lizzy_version != VERSION:
            warning("Version Mismatch (Client: {}, Server: {})".format(VERSION, lizzy_version))
        try:
            request.raise_for_status()
        except requests.RequestException:
            warning('Data Json:')
            print(json.dumps(data, indent=4))
            raise

    def wait_for_deployment(self, stack_id: str) -> [str]:
        retries = 3
        while retries:
            try:
                stack = self.get_stack(stack_id)
                status = stack["status"]
                retries = 3  # reset the number of retries
                yield status
                if status.endswith('_FAILED') or status.endswith('_COMPLETE'):
                    return status
            except Exception as e:
                retries -= 1
                yield 'Failed to get stack ({retries} retries left): {exception}.'.format(retries=retries,
                                                                                          exception=repr(e))

            time.sleep(10)
