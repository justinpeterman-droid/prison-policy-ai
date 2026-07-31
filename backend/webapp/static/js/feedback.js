document.addEventListener('DOMContentLoaded', () => {
    // Create the feedback widget container
    const widget = document.createElement('div');
    widget.id = 'feedback-widget';
    
    // Minimalist CSS for the widget
    const style = document.createElement('style');
    style.textContent = `
        #feedback-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            font-family: inherit;
        }
        #feedback-toggle {
            background: var(--surface, #1a1a2e);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #fff;
            padding: 10px 16px;
            border-radius: 20px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-size: 14px;
            transition: background 0.2s;
        }
        #feedback-toggle:hover {
            background: var(--surface-hover, #2a2a3e);
        }
        #feedback-form-container {
            display: none;
            position: absolute;
            bottom: 50px;
            right: 0;
            width: 300px;
            background: var(--surface, #1a1a2e);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        #feedback-form-container h4 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #fff;
        }
        #feedback-textarea {
            width: 100%;
            height: 80px;
            background: rgba(0,0,0,0.2);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #fff;
            padding: 8px;
            border-radius: 4px;
            font-size: 13px;
            resize: none;
            box-sizing: border-box;
            margin-bottom: 10px;
        }
        #feedback-textarea:focus {
            outline: none;
            border-color: rgba(255, 255, 255, 0.4);
        }
        .feedback-buttons {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }
        .feedback-buttons button {
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            border: none;
        }
        #feedback-cancel {
            background: transparent;
            color: #ccc;
        }
        #feedback-cancel:hover {
            color: #fff;
        }
        #feedback-submit {
            background: #c9971c; /* Gold */
            color: #000;
            font-weight: bold;
        }
        #feedback-submit:hover {
            background: #e6b230;
        }
        #feedback-status {
            font-size: 12px;
            margin-top: 8px;
            text-align: center;
            color: #c9971c;
            display: none;
        }
    `;
    document.head.appendChild(style);

    // Widget HTML
    widget.innerHTML = `
        <div id="feedback-toggle">💬 Feedback</div>
        <div id="feedback-form-container">
            <h4>Suggest an Improvement</h4>
            <textarea id="feedback-textarea" placeholder="What could be better on this page?"></textarea>
            <div class="feedback-buttons">
                <button id="feedback-cancel">Cancel</button>
                <button id="feedback-submit">Submit</button>
            </div>
            <div id="feedback-status"></div>
        </div>
    `;
    document.body.appendChild(widget);

    // Interactivity
    const toggle = document.getElementById('feedback-toggle');
    const formContainer = document.getElementById('feedback-form-container');
    const cancelBtn = document.getElementById('feedback-cancel');
    const submitBtn = document.getElementById('feedback-submit');
    const textarea = document.getElementById('feedback-textarea');
    const status = document.getElementById('feedback-status');

    toggle.addEventListener('click', () => {
        const isVisible = formContainer.style.display === 'block';
        formContainer.style.display = isVisible ? 'none' : 'block';
        if (!isVisible) {
            textarea.focus();
            status.style.display = 'none';
        }
    });

    cancelBtn.addEventListener('click', () => {
        formContainer.style.display = 'none';
        textarea.value = '';
    });

    submitBtn.addEventListener('click', async () => {
        const text = textarea.value.trim();
        if (!text) return;

        submitBtn.disabled = true;
        status.style.display = 'block';
        status.textContent = 'Submitting...';

        try {
            const res = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comment: text,
                    url: window.location.href
                })
            });

            if (res.ok) {
                status.textContent = 'Feedback submitted — thank you!';
                setTimeout(() => {
                    formContainer.style.display = 'none';
                    textarea.value = '';
                    submitBtn.disabled = false;
                    status.style.display = 'none';
                }, 2000);
            } else {
                // Distinguish failure types so a broken server config isn't
                // invisible. Server sends { error } detail — log it for admins.
                let detail = '';
                try { detail = (await res.json()).error || ''; } catch (e) {}
                if (detail) console.error('Feedback submit failed:', res.status, detail);

                let msg;
                if (res.status === 401) {
                    msg = 'Your session expired — reload the page and try again.';
                } else if (res.status === 429) {
                    msg = 'Too many submissions — please wait a few minutes.';
                } else if (res.status === 413) {
                    msg = 'That message is too long — please shorten it.';
                } else {
                    msg = 'Feedback couldn’t be saved (server error). Please let an admin know.';
                }
                status.textContent = msg;
                submitBtn.disabled = false;
            }
        } catch (err) {
            status.textContent = 'Network error — check your connection and try again.';
            submitBtn.disabled = false;
        }
    });
});
