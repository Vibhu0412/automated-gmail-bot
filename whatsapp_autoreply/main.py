import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from reply_engine import get_reply

options = webdriver.ChromeOptions()
options.add_argument("--user-data-dir=selenium_session")  # keeps you logged in
driver = webdriver.Chrome(options=options)

driver.get("https://web.whatsapp.com")
print("⏳ Scan the QR code and press Enter...")
input()

print("✅ Logged in. Waiting for messages...")


def find_new_message():
    try:
        unread_chats = driver.find_elements(By.CLASS_NAME, "_2aBzC")
        return unread_chats[0] if unread_chats else None
    except:
        return None


def read_last_message():
    messages = driver.find_elements(By.CLASS_NAME, "_21Ahp")
    return messages[-1].text if messages else ""


def send_reply(text):
    msg_box = driver.find_element(By.XPATH, '//div[@title="Type a message"]')
    msg_box.click()
    msg_box.send_keys(text + Keys.ENTER)


while True:
    new_chat = find_new_message()
    if new_chat:
        new_chat.click()
        time.sleep(2)

        last_msg = read_last_message()
        print(f"📩 Message received: {last_msg}")

        reply = get_reply(last_msg)
        print(f"🤖 Replying with: {reply}")
        send_reply(reply)

        time.sleep(3)

    time.sleep(2)
