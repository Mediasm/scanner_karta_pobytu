import os
import asyncio
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from telegram.ext import ApplicationBuilder

# Load environment variables from .env file
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBPAGE_URL = "https://webqms.lublin.uw.gov.pl/"

async def send_telegram_message(token, chat_id, message):
    application = ApplicationBuilder().token(token).build()
    await application.bot.send_message(chat_id=chat_id, text=message)

def wait_for_dalej_button(driver):
    try:
        dalej_button_xpath = "//button[contains(@class, 'footer-btn') and contains(text(), 'Dalej')]"
        dalej_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, dalej_button_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView();", dalej_button)
        driver.execute_script("arguments[0].click();", dalej_button)
        return True
    except Exception as e:
        print(f"Error clicking Dalej button: {e}")
        return False

def setup_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

try:
    # Initialize the Selenium WebDriver with headless options
    driver = setup_selenium_driver()

    # Step 1: Go to the webpage
    driver.get(WEBPAGE_URL)

    # Step 2: Wait for and click the registration button
    registration_button_xpath = "//button[contains(@class, 'operation-button') and contains(text(), 'Rejestracja – składanie wniosku o legalizację pobytu dla cudzoziemców')]"
    registration_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, registration_button_xpath))
    )
    registration_button.click()

    # Step 3: Wait for the "Dalej" button and remove any overlays if present
    success = wait_for_dalej_button(driver)
    if not success:
        raise Exception("Failed to click the 'Dalej' button.")

    # Step 4: Check if the specified message is present on the next page
    no_reservations_message_xpath = "//h5[contains(text(), 'Brak dostępnych rezerwacji w okresie od 01.02.2025 do 02.04.2025')]"
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, no_reservations_message_xpath))
        )
        print("No available reservations found.")
    except:
        # If the element is not found, notify via Telegram
        print("Notification sent via Telegram.")
        message = f"Available reservations found! Check the webpage: {WEBPAGE_URL}"
        asyncio.run(send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message))

finally:
    # Close the browser
    driver.quit()