document.addEventListener('DOMContentLoaded', function() {
    // Question Form Handling
    const questionForm = document.getElementById('questionForm');
    if (questionForm) {
        questionForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const question = document.getElementById('question').value;
            const loadingIndicator = document.getElementById('loadingIndicator');
            const answerSection = document.getElementById('answerSection');
            
            loadingIndicator.classList.remove('hidden');
            answerSection.classList.add('hidden');
            
            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question }),
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    document.getElementById('answer').textContent = data.answer;
                    
                    const sourcesDiv = document.getElementById('sources');
                    sourcesDiv.innerHTML = '';
                    
                    data.sources.forEach(source => {
                        const sourceLink = document.createElement('a');
                        sourceLink.href = source.url;
                        sourceLink.className = 'block p-2 hover:bg-gray-100 rounded text-blue-600 hover:text-blue-800';
                        sourceLink.textContent = `Source: ${source.document} (Paragraph ${source.paragraph_id})`;
                        sourcesDiv.appendChild(sourceLink);
                    });
                    
                    answerSection.classList.remove('hidden');
                } else {
                    alert(data.message || 'Error processing question');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error processing question');
            } finally {
                loadingIndicator.classList.add('hidden');
            }
        });
    }

    // Document Upload Form Handling
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    alert('Document uploaded successfully');
                    location.reload();
                } else {
                    alert(data.error || 'Error uploading document');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error uploading document');
            }
        });
    }
});