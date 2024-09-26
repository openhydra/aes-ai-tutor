import requests
from aitutor.server.utils import api_address

def create_default_kb():
    base_url = api_address()
    # 创建知识库的API端点
    create_kb_url = f"{base_url}/knowledge_base/create_knowledge_base"

    # 上传文件的API端点
    upload_docs_url = f"{base_url}/knowledge_base/upload_docs"

    # 创建知识库的请求数据
    create_kb_data = {
    "user_id": "build-in",
    "kb_name": "xedu",
    "vector_store_type": "faiss",
    "kb_info": "xedu 知识库",
    "embed_model": "bge-large-zh-v1.5",
    "is_private": "false"
    }

    # 创建知识库
    response = requests.post(create_kb_url, json=create_kb_data)
    if response.status_code == 200:
        print("知识库创建成功")
    else:
        print("知识库创建失败", response.text)

    # 上传文件的请求数据
    upload_files = [
        ("files", ("about.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/about.txt", "rb"), "text/plain")),
        ("files", ("basedeploy.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/basedeploy.txt", "rb"), "text/plain")),
        ("files", ("basedt.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/basedt.txt", "rb"), "text/plain")),
        ("files", ("baseml.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/baseml.txt", "rb"), "text/plain")),
        ("files", ("basenn.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/basenn.txt", "rb"), "text/plain")),
        ("files", ("easydl.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/easydl.txt", "rb"), "text/plain")),
        ("files", ("how_to_quick_start.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/how_to_quick_start.txt", "rb"), "text/plain")),
        ("files", ("how_to_use.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/how_to_use.txt", "rb"), "text/plain")),
        ("files", ("mmedu.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/mmedu.txt", "rb"), "text/plain")),
        ("files", ("xedu_hub.txt", open("/root/aes-ai-tutor/libs/aitutor/data/knowledge_base/xedu/content/xedu_hub.txt", "rb"), "text/plain")),
    ]

    # 构建请求体
    data = {
        "user_id": "build-in",
        "kb_name": "xedu",
        "override": "true",
        "to_vector_store": "true",
    }

    # 上传文件到知识库
    response = requests.post(upload_docs_url, data=data, files=upload_files)
    if response.status_code == 200:
        print("文件上传成功")
    else:
        print("文件上传失败", response.text)
