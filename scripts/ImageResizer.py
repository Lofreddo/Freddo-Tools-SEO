import streamlit as st
from PIL import Image
import io
import zipfile

def resize_image(image, width, height, resize_method, output_format):
    img = Image.open(image)
    
    if resize_method == "Redimensionner":
        img = img.resize((width, height), Image.LANCZOS)
    elif resize_method == "Tronquer":
        img = img.crop((0, 0, width, height))
    
    return img

def main():
    st.title("Image Resizer")

    uploaded_files = st.file_uploader("Choisissez les images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    
    width = st.number_input("Entrez la nouvelle largeur", min_value=1, value=100)
    height = st.number_input("Entrez la nouvelle hauteur", min_value=1, value=100)

    resize_method = st.selectbox("Méthode de redimensionnement", ["Redimensionner", "Tronquer"])
    output_format = st.selectbox("Format de sortie", ["jpg", "png", "webp"])

    if uploaded_files and st.button("Redimensionner les images"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for uploaded_file in uploaded_files:
                img = resize_image(uploaded_file, width, height, resize_method, output_format)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format=output_format.upper())
                zip_file.writestr(f"{uploaded_file.name.split('.')[0]}.{output_format}", img_buffer.getvalue())

        st.success("Images redimensionnées avec succès !")
        st.download_button(
            label="Télécharger les images redimensionnées",
            data=zip_buffer.getvalue(),
            file_name=f"resized_images.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
