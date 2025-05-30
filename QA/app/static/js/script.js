document.addEventListener('DOMContentLoaded', function () {
    const sendBtn = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const uploadImage = document.getElementById('upload-image');
    const uploadText = document.getElementById('upload-text');
    const uploadZip = document.getElementById('upload-zip');
    const fileInputImage = document.getElementById('file-input-image');
    const fileInputText = document.getElementById('file-input-text');
    const fileInputZip = document.getElementById('file-input-zip');

    sendBtn.addEventListener('click', sendMessage);

    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (e.shiftKey) return;
            e.preventDefault();
            sendMessage();
        }
    });

    window.onload = function () {
        const welcomeMessage = `
            <div class="message bot">
                <img src="/static/images/doctor.png" alt="医生头像" class="avatar">
                <div class="text">你好，我是医疗智能体。您可以直接输入问题，也可以点击图标上传文件。</div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', welcomeMessage);
        chatBox.scrollTop = chatBox.scrollHeight;
    };

    function sendMessage() {
        const inputText = userInput.value.trim();
        const mode = document.getElementById('mode-select').value;

        if (inputText === '') {
            alert('输入内容不能为空！');
            return;
        }

        const userMessage = `
            <div class="message user">
                <img src="/static/images/people.jpg" alt="用户头像" class="avatar">
                <div class="text">${escapeHtml(inputText)}</div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', userMessage);

        if (mode === 'qa') {
            fetch('/query?question=' + encodeURIComponent(inputText))
                .then(response => response.json())
                .then(data => showBotMessage(data.answer || '抱歉，没有查询到答案。'))
                .catch(() => showBotMessage('抱歉，问答系统出错了，请稍后再试。'));
        } else if (mode === 'pos' || mode === 'ner' || mode === 'summary') {
            const formData = new FormData();
            formData.append('text', inputText);
            formData.append('type', mode);

            fetch('/upload_document', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => showBotMessage(data.result || '无分析结果返回。'))
            .catch(() => showBotMessage('文档处理失败，请稍后再试。'));
        }


        chatBox.scrollTop = chatBox.scrollHeight;
        userInput.value = '';
    }

    function showBotMessage(text) {
        const botMessage = `
            <div class="message bot">
                <img src="/static/images/doctor.png" alt="医生头像" class="avatar">
                <div class="text">${text}</div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', botMessage);
        chatBox.scrollTop = chatBox.scrollHeight;

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = text;
        const plainText = tempDiv.textContent || tempDiv.innerText || "";
        document.getElementById('resultDisplay').innerText = plainText;
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]).replace(/\n/g, '<br>');
    }

    uploadImage.addEventListener('click', () => fileInputImage.click());
    uploadText.addEventListener('click', () => fileInputText.click());
    uploadZip.addEventListener('click', () => fileInputZip.click());

    fileInputImage.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const question = prompt("请输入与图片相关的问题：");
        if (!question || question.trim() === "") {
            alert("问题不能为空！");
            return;
        }

        const imageUrl = URL.createObjectURL(file);
        URL.revokeObjectURL(imageUrl);
        const userMessage = `
            <div class="message user">
                <img src="/static/images/people.jpg" alt="用户头像" class="avatar">
                <div class="text">
                    <img src="${imageUrl}" alt="用户图片" style="max-width: 300px; border-radius: 8px;"><br>
                    ${escapeHtml(question)}
                </div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', userMessage);
        chatBox.scrollTop = chatBox.scrollHeight;

        const formData = new FormData();
        formData.append('image', file);
        formData.append('question', question);

        fetch('/visual_qa', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            showBotMessage(escapeHtml(data.answer || "未能理解图像内容。"));
        })
        .catch(() => {
            showBotMessage("图像问答失败，请稍后重试。");
        });

        fileInputImage.value = '';
    });

    fileInputText.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const mode = document.getElementById('mode-select').value;

        const fileName = escapeHtml(file.name);
        const userMessage = `
            <div class="message user">
                <img src="/static/images/people.jpg" alt="用户头像" class="avatar">
                <div class="text">已上传文件：${fileName}</div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', userMessage);
        chatBox.scrollTop = chatBox.scrollHeight;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', mode);

        fetch('/upload_document', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            addMessageToChatBox(data.result, "bot", true);
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = data.result;
            document.getElementById("resultDisplay").innerText = tempDiv.innerText;
        })
        .catch(error => {
            alert('处理失败：' + error);
        });

        fileInputText.value = '';  // 重置输入框，允许重复上传同一文件
    });


    fileInputZip.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (file) {
            // 👇 显示用户上传提示
            const userMessage = `
                <div class="message user">
                    <img src="/static/images/people.jpg" alt="用户头像" class="avatar">
                    <div class="text">已上传压缩包：${escapeHtml(file.name)}</div>
                </div>
            `;
            chatBox.insertAdjacentHTML('beforeend', userMessage);
            chatBox.scrollTop = chatBox.scrollHeight;

            // 👇 开始上传
            uploadFile(file, 'zip').finally(()=>{
                fileInputZip.value='';
            });
        }
    });


    function uploadFile(file, type) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type);

        fetch('/upload_document', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            const botMessage = `
                <div class="message bot">
                    <img src="/static/images/doctor.png" alt="机器人头像" class="avatar">
                    <div class="text">${data.result}</div>
                </div>
            `;
            chatBox.insertAdjacentHTML('beforeend', botMessage);
            chatBox.scrollTop = chatBox.scrollHeight;
        })
        .catch(error => {
            console.error('上传失败', error);
            alert('上传失败，请重试\n错误信息:'+error.message);
        });
    }


    function addMessageToChatBox(text, sender, isHtml = false) {
        const avatar = sender === "user" ? "people.jpg" : "doctor.png";
        const message = `
            <div class="message ${sender}">
                <img src="/static/images/${avatar}" alt="头像" class="avatar">
                <div class="text">${isHtml ? text : escapeHtml(text)}</div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', message);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});

// 下载功能（不放入 DOMContentLoaded 以避免重复绑定）
document.getElementById("downloadBtn").onclick = function () {
    const type = document.getElementById("mode-select").value;

    if (type === 'zip') {
        // 处理zip模式，调用GET接口下载压缩包
        // 需要有window.folderName（即后端解压文件夹名）
        if (!window.folderName) {
            alert("请先上传并处理压缩包！");
            return;
        }
        const url = `/download_zip_images?folder=${encodeURIComponent(window.folderName)}`;
        const a = document.createElement("a");
        a.href = url;
        a.download = `${window.folderName}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } else {
        // 其它模式，调用已有的文本下载接口
        const result = document.getElementById("resultDisplay").innerText;
        if (!result) {
            alert("当前无可下载内容，请先进行操作。");
            return;
        }

        const formData = new FormData();
        formData.append("text", result);
        formData.append("type", type);

        fetch("/download_result", {
            method: "POST",
            body: formData
        })
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = type + "_result.txt";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        })
        .catch(err => {
            alert("下载失败，请稍后再试。");
            console.error("下载出错：", err);
        });
    }
};
