/**
 * Handles client‑side interaction for the Dagen reels generator.
 *
 * This script reads the article URL from the input field, displays a
 * status message, and calls a placeholder backend endpoint to
 * generate the video.  Replace the fetch call with your actual API
 * endpoint that triggers the Python pipeline on the server.
 */

document.addEventListener('DOMContentLoaded', () => {
  const generateBtn = document.getElementById('generateBtn');
  const articleUrl = document.getElementById('articleUrl');
  const statusDiv = document.getElementById('status');
  const resultDiv = document.getElementById('result');

  generateBtn.addEventListener('click', async () => {
    const url = articleUrl.value.trim();
    if (!url) {
      statusDiv.textContent = 'Vennligst lim inn en gyldig artikkel‑URL.';
      return;
    }
    // Disable UI while processing
    generateBtn.disabled = true;
    statusDiv.textContent = 'Genererer video … dette kan ta noen minutter.';
    resultDiv.textContent = '';

    try {
      // Call the backend convert endpoint.  It returns an MP4 file by default.
      const response = await fetch('/api/convert?url=' + encodeURIComponent(url));
      if (!response.ok) {
        throw new Error('Serverfeil: ' + response.status);
      }
      // Read the response as a Blob (binary data)
      const blob = await response.blob();
      // Create a temporary object URL for the video file
      const videoUrl = URL.createObjectURL(blob);
      statusDiv.textContent = 'Video generert!';
      const videoLink = document.createElement('a');
      videoLink.href = videoUrl;
      videoLink.download = 'dagen_reel.mp4';
      videoLink.textContent = 'Last ned video';
      resultDiv.appendChild(videoLink);
    } catch (err) {
      console.error(err);
      statusDiv.textContent = 'Det oppstod en feil ved generering av video.';
    } finally {
      generateBtn.disabled = false;
    }
  });
});
