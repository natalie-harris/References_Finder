from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options

import openai
import glob
import tiktoken
import time
import os
import requests
import PyPDF2

import pytesseract
from PIL import Image
import pdf2image

def wait_for_downloads_to_finish(download_dir, timeout=300):
    """
    Wait for the downloads in the provided directory to finish.
    Args:
        download_dir (str): The directory where Chrome saves downloads.
        timeout (int): Maximum time (in seconds) to wait for downloads to finish.
    Returns:
        bool: True if downloads finished within the timeout, False otherwise.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not any(fname.endswith('.crdownload') for fname in os.listdir(download_dir)):
            return True  # All downloads finished
        time.sleep(1)
    return False  # Timeout reached

def download_pdf(driver, link, download_dir):  

    if link not in downloaded_urls:  

        # Navigate to the link to initiate download
        driver.get(link)

        time.sleep(1.5)
        
        # Wait for the download to finish
        if not wait_for_downloads_to_finish(download_dir):
            print("Warning: Not all downloads may have finished!")

        downloaded_urls.add(link)

def wait():
    input("Waiting... ")
    return

def is_link_valid(url):
    try:
        response = requests.head(url, allow_redirects=True)  # HEAD is faster than GET, since it doesn't download the body content
        return response.status_code == 200
    except requests.RequestException:
        return False

def extract_text_from_scanned_pdf(file_path, poppler_bin_path):
    # Convert PDF to list of images
    images = pdf2image.convert_from_path(file_path, poppler_path=poppler_bin_path)

    # Extract text from each image
    texts = []
    for img in images:
        texts.append(pytesseract.image_to_string(img))
    
    return "\n".join(texts)

def extract_text(pdf_path):
    with open(pdf_path, 'rb') as file:
        pdf = PyPDF2.PdfReader(file)
        text = " ".join(page.extract_text() for page in pdf.pages)
    return text  # Using the extract_dois function from above

def get_tokenized_length(text, model, examples=[]):

    for example in examples:
        text += example["content"]

    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(text))
    return num_tokens

def build_last_chunk(system_message, text, end_message="\n\nEND\n\n", use_gpt4=False, examples=[]):
    system_message_length = len(system_message) + len(end_message)
    max_token_length = 4096
    base_multiplier = 4
    safety_multiplier = .9  # used just in case local tokenizer works differently than openai's

    # start at the end of the text
    i = len(text)

    # get initial text length values
    multiplier = base_multiplier
    user_message_length = int(max_token_length * multiplier) - system_message_length
    start_index = i - user_message_length
    if start_index < 0:  # If the text is smaller than the chunk size, just use the entire text
        start_index = 0
    message = system_message + text[start_index:i] + end_message
    token_length = get_tokenized_length(message, 'gpt-3.5-turbo', examples)
    
    # while text is too long for openai model, keep reducing size and try again
    while token_length > int(max_token_length * safety_multiplier):
        multiplier *= .95
        user_message_length = int(max_token_length * multiplier) - system_message_length
        start_index = i - user_message_length
        if start_index < 0:  # Ensure the start index never goes below 0
            start_index = 0
        message = system_message + text[start_index:i] + end_message
        token_length = get_tokenized_length(message, 'gpt-3.5-turbo', examples)
    
    # return the final chunk
    return [system_message, text[start_index:i] + end_message]

def get_chatgpt_response(system_message, user_message, temp, use_gpt4=False, examples=[]):
    gpt_model = ''
    total_message = system_message + user_message
    if use_gpt4:
        num_tokens = get_tokenized_length(total_message, 'gpt-4', examples)
        gpt_model = 'gpt-4'
        # if num_tokens < 8192:
        #     gpt_model = 'gpt-4'
        # else:
        #     gpt_model = 'gpt-4-32k'
    else:
        num_tokens = get_tokenized_length(total_message, 'gpt-3.5-turbo', examples)
        if num_tokens < 4096:
            gpt_model = 'gpt-3.5-turbo'
        else:
            gpt_model = 'gpt-3.5-turbo-16k'

    new_messages = []    
    if len(examples) > 0:
        new_messages.append({"role": "system", "content": system_message})
        for example in examples:
            new_messages.append(example)
        new_messages.append({"role": "user", "content": user_message})
    else:
        new_messages.append({"role": "user", "content": user_message})
        new_messages.append({"role": "system", "content": system_message})

    # print(len(new_messages))

    got_response = False
    while not got_response:
        try:

            response = openai.ChatCompletion.create (
                model = gpt_model,
                messages = new_messages,
                temperature = temp
            )

            generated_text = response['choices'][0]['message']['content']
            got_response = True
            return generated_text

        except openai.error.RateLimitError as err:
            if 'You exceeded your current quota' in str(err):
                print("You've exceeded your current billing quota. Go check on that!")
                exit()
            num_seconds = 3
            print(f"Waiting {num_seconds} seconds due to high volume of {gpt_model} users.")
            time.sleep(3)

        except openai.error.APIError as err:
            print("An error occured. Retrying request.")

        except openai.error.Timeout as err:
            print("Request timed out. Retrying...")

        except openai.error.ServiceUnavailableError as err:
            num_seconds = 3
            print(f"Server overloaded. Waiting {num_seconds} seconds and retrying request.")

# create a new Options object
chrome_options = Options()
# add the "--headless" argument
# chrome_options.add_argument("--headless")

# set up openai api
openai_key = "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"
openai.api_key = openai_key

download_dir = r'E:\NIMBioS\SBW\SBW Literature\References Finder'
prefs = {
    "download.default_directory": download_dir, 
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True  # It will not display PDF directly in chrome
}
chrome_options.add_experimental_option('prefs', prefs)


system_message_1 = 'Please extract all the titles of documents from this reference list:\n'
system_message_2 = "Please extract all the titles of documents that are likely about eastern spruce budworm outbreaks. Only include titles about eastern spruce budworm outbreaks\n"

poppler_bin_path = r'C:\Users\natal\OneDrive\Documents\GitHub\References_Finder\windows_venv\poppler-23.08.0\Library\bin'
file_path = r'E:\NIMBioS\SBW\SBW Literature\Canada Government\pdfs\8982.pdf'
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = tesseract_path

downloaded_urls = set()

pdf_files = glob.glob(r"E:\NIMBioS\SBW\SBW Literature\Canada Government\pdfs\*.pdf")
 
initial_url = 'https://google.com/'

# Set up Selenium driver
driver = webdriver.Chrome(options=chrome_options)
driver.get(initial_url)
has_completed_check = False

for file_path in pdf_files:

    print(file_path)

    try:
        text = extract_text(file_path)
        if len(text) < 1000:
            text = extract_text_from_scanned_pdf(file_path, poppler_bin_path)
    except ValueError:
        text = extract_text_from_scanned_pdf(file_path, poppler_bin_path)
    
    last_chunk = build_last_chunk(system_message_1, text)

    if len(last_chunk) <= 0:
        os.exit()

    print(last_chunk)
    if len(last_chunk[1]) < 1000:
        continue

    response = get_chatgpt_response(system_message_1, last_chunk[1], 0)
    s2_response = get_chatgpt_response(system_message_2, response, 0)
    

    search_terms = s2_response
    search_terms = search_terms.split('\n')

    print(search_terms)
    if len(search_terms) <= 1:
        continue


    if not has_completed_check:
        wait()

    new_url = f'https://scholar.google.com/scholar?q={search_terms[0]}'
    driver.get(new_url)

    if not has_completed_check:
        wait()
        has_completed_check = True

    for search_term in search_terms:
        if len(search_term) < 9:
            continue

        search_term = search_term.replace(' ', '+')
        time.sleep(1)

        new_url = f'https://scholar.google.com/scholar?q={search_term}'
        driver.get(new_url)

        try:
            pdf_links = driver.find_elements(By.XPATH, "//a[./span[contains(., 'PDF')]]")
            hrefs = [pdf_link.get_attribute('href') for pdf_link in pdf_links] 
            for href in hrefs:
                if is_link_valid(href):
                    download_pdf(driver, href, download_dir)
        except NoSuchElementException:
            print("No PDF link found on the page.")

driver.close()
