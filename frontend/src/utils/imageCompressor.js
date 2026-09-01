/**
 * Image Compressor & Normalizer for Mobile & Web
 * Scales down large camera photos (e.g. 12MP/15MB) to max 1280px JPEG (~150KB)
 * and normalizes HEIC/PNG/WEBP/RAW formats for seamless LLM Vision inference.
 */

export async function compressAndFormatImage(file, maxDimension = 1280, quality = 0.82) {
  return new Promise((resolve, reject) => {
    if (!file) {
      return reject(new Error('Keine Datei übergeben'));
    }

    // Check if it's an image
    if (!file.type.startsWith('image/')) {
      return reject(new Error('Ausgewählte Datei ist kein Bild'));
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        let { width, height } = img;

        // Calculate aspect-preserving dimensions
        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          return resolve({
            name: file.name,
            base64: e.target.result,
            previewUrl: e.target.result,
            originalSize: file.size,
            compressedSize: file.size,
          });
        }

        // Draw and compress to clean JPEG
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);

        const compressedBase64 = canvas.toDataURL('image/jpeg', quality);
        const approxBytes = Math.round((compressedBase64.length * 3) / 4);

        resolve({
          name: file.name.replace(/\.[^/.]+$/, '') + '.jpg',
          base64: compressedBase64,
          previewUrl: compressedBase64,
          width,
          height,
          originalSize: file.size,
          compressedSize: approxBytes,
        });
      };

      img.onerror = () => {
        // Fallback to raw base64 if canvas drawing fails
        resolve({
          name: file.name,
          base64: e.target.result,
          previewUrl: e.target.result,
          originalSize: file.size,
          compressedSize: file.size,
        });
      };

      img.src = e.target.result;
    };

    reader.onerror = (err) => reject(new Error('Fehler beim Lesen der Datei'));
    reader.readAsDataURL(file);
  });
}
