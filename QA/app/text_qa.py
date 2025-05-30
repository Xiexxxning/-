import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# ✅ 初始化 OpenAI 客户端（ChatAnywhere）
client = OpenAI(
    api_key="sk-nNbADLnbiiF1I300YTtKO2RupigxjhFoOL7R3vIUVGm2DvFy",  # ← 你的 API key
    base_url="https://api.chatanywhere.tech/v1"
)

# ✅ 加载知识库
df = pd.read_csv("app/data/knowledge.csv")
questions = df["question"].fillna("").tolist()
answers = df["answer"].fillna("").tolist()

# ✅ 构建 TF-IDF 向量
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(questions)

# ✅ GPT 回答函数（只保留一份！）
def generate_gpt_answer(query, context_list):
    if context_list:
        context = "\n".join([f"{i+1}. {c}" for i, c in enumerate(context_list)])
        user_input = f"已知相关知识如下：\n{context}\n\n用户问题：{query}\n请用简洁、专业的中文回答："
    else:
        user_input = f"用户问题：{query}\n请你作为医学助手，基于你掌握的知识，简洁、专业地回答："

    messages = [
        {"role": "system", "content": "你是一个医学问答助手，请结合知识库提供专业准确的回答。"},
        {"role": "user", "content": user_input}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.5,
            max_tokens=512
        )
        # 确保正确访问响应内容
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"调用 GPT 接口失败：{e}"

# ✅ 主函数：从本地检索知识，调用 GPT
def get_answer(query, top_k=3, threshold=0.2):
    if not query.strip():
        return "请输入有效的问题。"

    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix)[0]
    scored = [(score, i) for i, score in enumerate(similarities) if score >= threshold]

    if scored:
        top_results = sorted(scored, reverse=True)[:top_k]
        related_contexts = [f"{questions[i]}：{answers[i]}" for _, i in top_results]
    else:
        related_contexts = []

    return generate_gpt_answer(query, related_contexts)
