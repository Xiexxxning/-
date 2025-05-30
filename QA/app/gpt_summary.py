
from openai import OpenAI

# ✅ 写死 API Key 和 Base URL（如已有全局配置模块也可从中导入）
client = OpenAI(
    api_key="sk-nNbADLnbiiF1I300YTtKO2RupigxjhFoOL7R3vIUVGm2DvFy",  # 🔁 替换为你自己的 ChatAnywhere API Key
    base_url="https://api.chatanywhere.tech/v1"
)

def generate_gpt_summary(text):
    """
    使用 GPT 接口生成中文摘要
    """
    messages = [
        {"role": "system", "content": "你是一个智能文本助手，擅长用简洁、准确的语言总结中文段落。"},
        {"role": "user", "content": f"请对以下内容进行摘要，要求简洁、通顺、保留核心信息：\n\n{text}"}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 或 gpt-4
            messages=messages,
            temperature=0.5,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"调用 GPT 出错：{e}"
