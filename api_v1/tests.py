import time

from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from celery.result import AsyncResult

from celery_tasks import tasks


DELAY = 1
MAX_ATTEMPTS_TO_GET_TASK_STATE = 5

def forget_task(guid):
    """
    Forget about the task with id <guid>
    """
    task = AsyncResult(
        '{}{}'.format(settings.MD5_TASK_ID_PREFIX, guid), 
        app=tasks.app
    )
    task.forget()

class Md5Tests(TestCase):

    def test_request_without_url(self):
        resp = self.client.post(reverse('document_send_url'))    
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def test_request_with_empty_url(self):
        resp = self.client.post(reverse('document_send_url'), {'url': ''})    
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    def get_guid(self, url):
        """
        Sends url of a file and returns tasks's GUID
        """
        resp = self.client.post(
            reverse('document_send_url'), 
            {'url': url}
        )    
        self.assertEqual(resp.status_code, 202)
        self.assertIn('GUID', resp.json())
        return resp.json().get('GUID')

    def test_request_with_correct_url(self):
        #getting guid        
        guid = self.get_guid('https://avatars.mds.yandex.net/get-pdb/777813/741bcd1f-da1f-402c-97d7-224fd9091747/s800')

        #checking result  
        try:      
            i = 0
            while True:
                resp = self.client.get(
                reverse('document_get_md5'),
                {'guid': guid}
                )
                json = resp.json()
                self.assertIn('state', json)
                state = json['state']
                #we are waiting for SUCCESS or FAILTURE state
                if state == 'FAILURE':
                    self.assertIn('traceback', json)
                    break
                elif state == 'SUCCESS':
                    self.assertIn('md5', json)
                    break
                i += 1
                time.sleep(DELAY)
                if i > MAX_ATTEMPTS_TO_GET_TASK_STATE:
                    self.fail('The task is executing too much time')
        except Exception as e:
            raise e
        finally:    #forget about the task
            forget_task(guid)

    def test_request_with_incorrect_url(self):
        #getting guid
        guid = self.get_guid('[eq]') #incorrect url

        #checking result      
        try:   
            i = 0
            while True:   
                resp = self.client.get(
                    reverse('document_get_md5'),
                    {'guid': guid}
                )
                json = resp.json()
                self.assertIn('state', json)
                state = json['state']    
                self.assertNotEqual(state, 'SUCCESS')
                #we are waiting for FAILTURE state
                if state == 'FAILURE':
                    self.assertIn('traceback', json)
                    break
                i += 1
                time.sleep(DELAY)
                if i > MAX_ATTEMPTS_TO_GET_TASK_STATE:
                    self.fail('The task is executing too much time')
        except Exception as e:
            raise e
        finally: #forget about the task
            forget_task(guid)


