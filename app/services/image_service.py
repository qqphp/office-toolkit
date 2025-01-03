from alibabacloud_imageseg20191230.client import Client as imageseg20191230Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_imageseg20191230 import models as imageseg_20191230_models
from alibabacloud_tea_util import models as util_models
from flask import current_app
import os
import uuid
import time
import json
import requests

def create_ali_client():
    """
    创建阿里云客户端
    """
    config = open_api_models.Config(
        access_key_id=current_app.config['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        access_key_secret=current_app.config['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
    )
    config.endpoint = current_app.config['ALIBABA_CLOUD_ENDPOINT']
    return imageseg20191230Client(config)

def get_async_job_result(client, job_id: str, max_retries: int = 10, retry_interval: int = 2):
    """
    获取异步任务的处理结果
    
    Args:
        client: 阿里云客户端
        job_id: 任务ID
        max_retries: 最大重试次数
        retry_interval: 重试间隔(秒)
    """
    for i in range(max_retries):
        try:
            request = imageseg_20191230_models.GetAsyncJobResultRequest(job_id=job_id)
            response = client.get_async_job_result(request)
            
            if response.body.data.status == "PROCESS_SUCCESS":
                # 任务处理成功，解析结果
                result = json.loads(response.body.data.result)
                return result
            elif response.body.data.status == "PROCESS_FAILED":
                # 任务处理失败
                raise Exception(f"图片处理失败: 任务执行失败")
            else:
                # 任务仍在处理中，等待后重试
                time.sleep(retry_interval)
                continue
                
        except Exception as e:
            current_app.logger.error(f"获取异步任务结果失败: {str(e)}")
            raise
            
    raise Exception("任务处理超时")

def remove_background(input_path: str) -> str:
    """
    使用阿里云通用高清分割服务移除图片背景
    """
    try:
        # 创建客户端
        client = create_ali_client()
        
        # 使用文件流方式读取图片
        with open(input_path, 'rb') as f:
            # 创建请求
            request = imageseg_20191230_models.SegmentHDCommonImageAdvanceRequest(
                image_url_object=f  # 正确的参数名是 image_url_object 而不是 image_urlobject
            )
            runtime = util_models.RuntimeOptions()
            
            # 调用API
            response = client.segment_hdcommon_image_advance(request, runtime)

            # 获取任务ID
            job_id = response.body.request_id
        
        # 获取异步处理结果
        result = get_async_job_result(client, job_id)
        
        if result and 'imageUrl' in result:
            # 处理返回的图片URL
            result_image_url = result['imageUrl']
            
            # 下载处理后的图片
            result_image_content = requests.get(result_image_url).content
            
            # 生成输出文件名
            output_filename = f"{uuid.uuid4()}.png"
            output_path = os.path.join(current_app.config['REMOVE_BG_FOLDER'], output_filename)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存处理后的图片
            with open(output_path, 'wb') as f:
                f.write(result_image_content)
            
            # 清理原始文件
            os.remove(input_path)
            
            return f"/static/uploads/remove_bg/{output_filename}"
        else:
            raise Exception("图片处理失败：未获取到有效的图片URL")
            
    except Exception as e:
        current_app.logger.error(f"移除背景失败: {str(e)}")
        if os.path.exists(input_path):
            os.remove(input_path)
        raise Exception(f"处理图片时发生错误: {str(e)}")