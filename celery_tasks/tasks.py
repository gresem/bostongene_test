import os
import sys
import requests
import shutil
import hashlib

from celery import Celery
import django

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'bostongene_test.settings'
django.setup()

from django.conf import settings

app = Celery('tasks')
app.conf.update(
    BROKER_URL=settings.RABBIT_URL,
    CELERY_RESULT_BACKEND=settings.MONGO_URL,
    CELERYD_CONCURRENCY=2,
)

@app.task(name='download', ignore_result=True)
def download(url):
    """
    Downloads a file from <url> to the dir <settings.TEMP_DIR>.
    The name of this file = task ID. 
    In the end executes the task named set_handling_result, 
    that calculates MD5 of the saved file. 
    In case of exception, the Exception's object will be passed in
    set_handling_result.
    """
    taskId = download.request.id
    exception = None
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            if not os.path.exists(settings.TEMP_DIR):
                os.makedirs(settings.TEMP_DIR)
            with open(os.path.join(settings.TEMP_DIR, download.request.id), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)       
        else:
            raise Exception('No file is avalible at the URL {url}. Response code: {code}'.format(
                url=url,
                code=r.status_code
                )
            )    
    except Exception as e:
        exception = e
    finally:
        set_handling_result.apply_async([taskId, exception], task_id='{}{}'.format(settings.MD5_TASK_ID_PREFIX, taskId))
    
@app.task(name='set_handling_result')
def set_handling_result(task_id, exception=None):
    """
    Calculated MD5 of the file named <task_id> and deletes this file
    after calculating. 
    The ID of this task = <settings.MD5_TASK_ID_PREFIX>+<task_id>
    If <exception> is not None, it will be raises here for storing
    result in backend.
    """
    if exception:
        raise exception
    md5 = hashlib.md5()
    fname = os.path.join(settings.TEMP_DIR, task_id)
    with open(fname, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    os.remove(fname)
    return md5.hexdigest()