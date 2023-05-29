import streamlit as st
import openai
import requests
import json
import os
import subprocess
import shutil

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
TERRAFORM_PATH = "/usr/bin/terraform"

# Define a function to interact with ChatGPT API
def interact_with_chatgpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a Terraform expert. Please generate only the code requested. Be sure to enclose both ends of the code in three backquotes."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    print("#### Prompt: ####\n\n" + prompt + "\n\n")
    print("#### Response: ####\n\n" + content + "\n\n")

    start_index = content.find("```")
    end_index = content.rfind("```")
    
    if start_index != -1 and end_index != -1 and start_index != end_index:
        code = content[start_index + 3: end_index].strip()
        return code
    else:
        raise Exception("コードが生成されていません。")

def validate_code(code):
    # Write generated code to a file
    directory_name = "hoge"
    os.makedirs(directory_name, exist_ok=True)
    os.chdir(directory_name)
    with open("code.tf", "w") as f:
        f.write(code)
    # Run "terraform validate"
    subprocess.run([TERRAFORM_PATH, "init"], capture_output=True, text=True)
    result = subprocess.run([TERRAFORM_PATH, "validate"], capture_output=True, text=True)
    os.chdir("../")
    shutil.rmtree(directory_name)
    return result

# Streamlit App
st.title("Terraformコード生成アプリ")
st.write("このアプリは、入力情報に基づいてTerraformコードを生成します。")

# Initialize session state
if "generated_code" not in st.session_state:
    st.session_state.generated_code = None

# Input fields
st.header("入力フィールド")
service_provider = st.text_input("サービスプロバイダ", "AWS")
other_field = st.text_input("その他の要件入力フィールド", "")

inputs = (service_provider, other_field)
# Generate code button
if st.button("コード生成"):
    prompt = f"Generate Terraform code.\nInput information：{inputs}\n\nCode:\n"
    generated_code = interact_with_chatgpt(prompt)
    st.code(generated_code)
    st.session_state.generated_code = generated_code

# Validate button
if st.button("バリデートチェック・自動修正"):
    generated_code = st.session_state.generated_code
    st.code(generated_code)
    st.header("バリデート・自動修正状況")
    validate_button = st.empty() # Create an empty placeholder for the button
    validation_status = st.empty()  # Create an empty placeholder for the validation status

    with validate_button.container():
        validate_button.info("Terraformコードをバリデート・自動修正しています...")  # Show a loading message
    result = validate_code(generated_code)  # Fix: Pass generated_code instead of corrected_code
    max_attempts = 3  # 最大試行回数
    attempt = 1

    while result.returncode !=0 and attempt <= max_attempts:
        # If validation fails, request code correction
        error = result.stderr
        #error = remove_ansi_escape_sequences(err)
        validation_status.error(f"エラー：{error}")
        prompt = f"The following Terraform code has an error:\n\n```\n{generated_code}\n```\n\nError: {error}\n\nCorrected code:\n\n"
        corrected_code = interact_with_chatgpt(prompt)
        result = validate_code(corrected_code)
        generated_code = corrected_code
        attempt += 1
    st.code(generated_code)
    st.success("コードのバリデーションが正常に終了しました。")
