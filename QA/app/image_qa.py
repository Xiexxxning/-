from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
from openai import OpenAI

# 初始化 BLIP 模型（一次）
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# 初始化 ChatAnywhere GPT
client = OpenAI(
    api_key="sk-nNbADLnbiiF1I300YTtKO2RupigxjhFoOL7R3vIUVGm2DvFy",
    base_url="https://api.chatanywhere.tech/v1"
)

# 生成图像描述
def generate_caption(image_file):
    image = Image.open(image_file).convert('RGB')
    inputs = processor(image, return_tensors="pt")
    out = model.generate(**inputs, max_new_tokens=100)
    caption = processor.decode(out[0], skip_special_tokens=True)
    
    # 让 GPT 优化成自然的中文描述
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "将英文图片描述转换成流畅的中文，不要添加额外解释。"},
            {"role": "user", "content": f"将以下图片描述翻译成自然的中文：{caption}"}
        ],
        temperature=0.2,
        max_tokens=100
    )
    return response.choices[0].message.content.strip()

# 结合用户问题进行视觉问答
def visual_question_answer(image_file, user_question):
    caption = generate_caption(image_file)  # 生成图片描述

    prompt = f"""
【图片描述】
{caption}

【用户问题】
{user_question}

请直接根据图片描述回答问题，不要提及“根据描述”或“无法看到图片”等内容。回答要简洁专业。"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专业的图像分析助手，直接根据给定的图片描述回答问题。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"调用 GPT 出错：{e}"
