import os
import zipfile
import shutil
import jieba
import uuid
import chardet
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw = f.read(10000)
    result = chardet.detect(raw)
    return result['encoding'] or 'utf-8'

def perform_text_mining(zip_path):
    try:
        # 1. 创建解压目录
        extract_dir = os.path.join("app", "data", "uploads", f"extracted_{uuid.uuid4().hex[:6]}")
        os.makedirs(extract_dir, exist_ok=True)
        print(f"解压目录已创建: {extract_dir}")

        # 2. 解压文件
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"文件已解压到: {extract_dir}")
        except zipfile.BadZipFile:
            return "错误：上传的文件不是有效的ZIP压缩包"
        except Exception as e:
            return f"解压失败: {str(e)}"

        # 3. 读取文本文件
        documents = []
        filenames = []
        txt_files_found = False

        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith('.txt'):
                    txt_files_found = True
                    filepath = os.path.join(root, file)
                    try:
                        encoding = detect_encoding(filepath)
                        print(f"正在处理文件: {filepath} (检测编码: {encoding})")
                        with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                            content = f.read()
                            if content.strip():  # 确保文件不是空的
                                documents.append(' '.join(jieba.cut(content)))
                                filenames.append(file)
                            else:
                                print(f"警告: 文件 {file} 是空的")
                    except Exception as e:
                        print(f"读取 {filepath} 失败：{e}")
                        continue

        if not txt_files_found:
            return "压缩包中未找到任何.txt文本文件"
        if not documents:
            return "压缩包中没有包含有效内容的文本文件"

        print(f"成功读取 {len(documents)} 个有效文档")

        # 4. 文本向量化
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(documents)

        # 5. 聚类分析
        k = min(3, len(documents))
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(X)

        # 6. 降维可视化（动态选择方法）
        n_samples = X.shape[0]
        if n_samples < 2:
            return "错误：至少需要2个文档才能进行分析"
        
        # 动态设置perplexity（5-30之间且小于样本数）
        perplexity = min(30, max(5, n_samples - 1)) if n_samples > 1 else 1
        
        try:
            if n_samples >= 5:  # 样本足够时使用t-SNE
                tsne = TSNE(
                    n_components=2,
                    perplexity=perplexity,
                    random_state=42,
                    init='pca'  # 更稳定的初始化方式
                )
                X_embedded = tsne.fit_transform(X.toarray())
                method_name = "t-SNE"
            else:  # 样本少时使用PCA
                from sklearn.decomposition import PCA
                pca = PCA(n_components=2)
                X_embedded = pca.fit_transform(X.toarray())
                method_name = "PCA"
        except Exception as e:
            print(f"降维失败: {e}, 改用PCA")
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2)
            X_embedded = pca.fit_transform(X.toarray())
            method_name = "PCA"

        # 7. 创建输出目录
        static_subdir = f"uploads/{os.path.basename(extract_dir)}"
        static_output_dir = os.path.join("app", "static", static_subdir)
        os.makedirs(static_output_dir, exist_ok=True)
        print(f"输出目录已创建: {static_output_dir}")

        # 8. 生成可视化图表
        # 降维图
        plt.figure(figsize=(10, 8))
        for i in range(len(X_embedded)):
            plt.scatter(X_embedded[i, 0], X_embedded[i, 1], alpha=0.6)
            plt.text(X_embedded[i, 0], X_embedded[i, 1], filenames[i], fontsize=8)
        plt.title(f"{method_name} 降维可视化 (共{len(documents)}个文档)")
        plot_path = os.path.join(static_output_dir, "dim_reduction_plot.png")
        plt.savefig(plot_path, bbox_inches='tight', dpi=150)
        plt.close()

        # 词云图
        wordcloud_paths = []
        for cluster_id in set(labels):
            cluster_docs = [documents[i] for i in range(len(documents)) if labels[i] == cluster_id]
            text = ' '.join(cluster_docs)
            try:
                wc = WordCloud(
                    font_path=os.path.join("app", "data", "simsun.ttc"),
                    background_color='white',
                    width=800,
                    height=400,
                    max_words=200,
                    collocations=False  # 避免重复词
                )
                wc.generate(text)
                wc_path = os.path.join(static_output_dir, f"wordcloud_{cluster_id}.png")
                wc.to_file(wc_path)
                wordcloud_paths.append(f"/static/{static_subdir}/wordcloud_{cluster_id}.png")
            except Exception as e:
                print(f"生成词云图失败(簇{cluster_id}): {e}")
                continue

        # 9. 构建HTML响应
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto;">
                    <h2 style="color: #2c3e50;">文本挖掘分析结果</h2>
                    <p>分析文档数: {len(documents)} | 聚类数: {k}</p>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h3 style="color: #3498db;">{method_name} 降维可视化</h3>
                        <img src="/static/{static_subdir}/dim_reduction_plot.png" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #3498db;">各类文本词云图</h3>"""
        
        for i, path in enumerate(wordcloud_paths):
            html += f"""<div style="margin-bottom: 30px;">
                        <h4 style="color: #2c3e50;">类别 {i+1}</h4>
                        <img src="{path}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
                      </div>"""
        
        html += "</div></div>"
        
        return html

    except Exception as e:
        print(f"文本挖掘过程中发生错误: {str(e)}")
        return f"处理过程中发生错误: {str(e)}"