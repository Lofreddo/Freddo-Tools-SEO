import streamlit as st
from PIL import Image
import os
import io
import zipfile

def resize_image(image, width, height):
    img = Image.open(image)
    img = img.resize((width, height), Image.LANCZOS)
    return img

def main():
    st.title("Image Resizer")

    uploaded_files = st.file_uploader("Choose images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    
    width = st.number_input("Enter new width", min_value=1, value=100)
    height = st.number_input("Enter new height", min_value=1, value=100)

    if uploaded_files and st.button("Resize Images"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for uploaded_file in uploaded_files:
                img = resize_image(uploaded_file, width, height)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                zip_file.writestr(uploaded_file.name, img_buffer.getvalue())

        st.success("Images resized successfully!")
        st.download_button(
            label="Download resized images",
            data=zip_buffer.getvalue(),
            file_name="resized_images.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
