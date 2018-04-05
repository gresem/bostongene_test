import requests
import shutil
import os
from datetime import datetime

from django.shortcuts import render
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult

from celery_tasks import tasks

class NewDocument(APIView):

    def post(self, request):
        url = request.data.get('url')
        if url:
            uid = tasks.download.apply_async([url]).id
            return Response({'GUID': uid}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'error': '"url" is required'}, status=status.HTTP_400_BAD_REQUEST)
           

class Md5(APIView):
    """docstring for Md5"""
    
    def get(self, request):
        guid = request.query_params.get('guid')
        if guid:
            task = AsyncResult('{}{}'.format(settings.MD5_TASK_ID_PREFIX, guid), app=tasks.app)
            ret = {'state': task.state}
            if task.failed():
                ret['traceback'] = task.traceback
                return Response(ret, status=status.HTTP_400_BAD_REQUEST)
            elif task.ready():
                ret['md5'] = task.result
                return Response(ret, status=status.HTTP_200_OK)
            else:
                return Response(ret, status=status.HTTP_409_CONFLICT)
        else:
            return Response({'error': '"guid" is required'}, status=status.HTTP_400_BAD_REQUEST)
        