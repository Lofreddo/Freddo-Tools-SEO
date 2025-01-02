import streamlit as st
from PIL import Image
import io
import zipfile

def resize_image(image, width, height, resize_method):
    img = Image.open(image)
    
    if resize_method == "Optimale":
        # Calculer le ratio pour le redimensionnement
        ratio = min(width / img.width, height / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        
        # Tronquer si nécessaire
        if img.width != width or img.height != height:
            left = (img.width - width) // 2
            top = (img.height - height) // 2
            right = left + width
            bottom = top + height
            img = img.crop((left, top, right, bottom))
    elif resize_method == "Tronquer":
        if img.width >= width and img.height >= height:
            left = (img.width - width) // 2
            top = (img.height - height) // 2
            right = left + width
            bottom = top + height
            img = img.crop((left, top, right, bottom))
        else:
            img = img.resize((width, height), Image.LANCZOS)
    elif resize_method == "Redimensionner":
        img = img.resize((width, height), Image.LANCZOS)
    
    return img

def save_image(img, output_format):
    if output_format.lower() == 'jpg':
        output_format = 'jpeg'  # PIL utilise 'jpeg' au lieu de 'jpg'
    if output_format.lower() == 'jpeg':
        # Convertir en RGB si nécessaire
        if img.mode != 'RGB':
            img = img.convert('RGB')
    
    img_buffer = io.BytesIO()
    img.save(img_buffer, format=output_format.upper())
    return img_buffer.getvalue()

def main():
    st.title("Image Resizer")

    uploaded_files = st.file_uploader("Choisissez les images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    
    width = st.number_input("Entrez la nouvelle largeur", min_value=1, value=100)
    height = st.number_input("Entrez la nouvelle hauteur", min_value=1, value=100)

    resize_method = st.selectbox("Méthode de redimensionnement", ["Optimale", "Redimensionner", "Tronquer"])
    output_format = st.selectbox("Format de sortie", ["jpg", "png", "webp"])

    if uploaded_files and st.button("Redimensionner les images"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for uploaded_file in uploaded_files:
                img = resize_image(uploaded_file, width, height, resize_method)
                img_data = save_image(img, output_format)
                zip_file.writestr(f"{uploaded_file.name.split('.')[0]}.{output_format}", img_data)

        st.success("Images redimensionnées avec succès !")
        st.download_button(
            label="Télécharger les images redimensionnées",
            data=zip_buffer.getvalue(),
            file_name=f"resized_images.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
