import asyncio
from pyppeteer import launch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re  # Import regex for improved text extraction

# Email configuration
email_user = 'email-to-send-from'
email_password = 'password'
send_to_email = 'email-tobesent'
subject = 'Holland2Stay Availability Update'

async def send_email(body, subject_line=subject):
    """Sends an email to the specified recipient."""
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = send_to_email
    msg['Subject'] = subject_line
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_user, email_password)
    server.sendmail(email_user, send_to_email, msg.as_string())
    server.quit()

async def fetch_page():
    """Launches a browser and fetches the page content."""
    # Adding extra args for headless Chrome on a server
    browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'], dumpio=True)
    page = await browser.newPage()
    await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36')
    await page.goto('https://holland2stay.com/residences?city%5Bfilter%5D=Amsterdam%2C24&page=1')
    return page, browser

occupied_previous_count = None  # Global variable to store the previous count of occupied units

async def check_listings():
    global occupied_previous_count
    """Checks the listings and sends an email if the occupied count changes or on the first check."""
    page, browser = await fetch_page()

    try:
        await page.waitForSelector('div[data-cy="FilterList-item"]', {'timeout': 30000})
        # Extract all text from relevant filters
        occupied_text = await page.evaluate('''() => {
            const occupiedLabel = [...document.querySelectorAll('div[data-cy="FilterList-item"] label')]
                                    .find(label => label.textContent.includes('Occupied'));
            return occupiedLabel ? occupiedLabel.textContent : 'Occupied (0)';
        }''')
        available_text = await page.evaluate('''() => {
            const availableLabel = [...document.querySelectorAll('div[data-cy="FilterList-item"] label')]
                                     .find(label => label.textContent.includes('Available in lottery'));
            return availableLabel ? availableLabel.textContent : 'Available in lottery (0)';
        }''')

        # Use regex to find numbers
        occupied_count = int(re.search(r'\((\d+)\)', occupied_text).group(1))
        available_count = int(re.search(r'\((\d+)\)', available_text).group(1))

        # Always send an email on the first check to show initial counts
        if occupied_previous_count is None:
            await send_email(f"Initial counts: {occupied_count} units occupied, {available_count} units available in lottery.")

        # Check for change in occupied count and send updates accordingly
        elif occupied_count != occupied_previous_count:
            if occupied_count < occupied_previous_count:
                await send_email(f"Update: Fewer units are occupied now. Current count: {occupied_count} occupied, {available_count} available in lottery.")
            elif occupied_count > occupied_previous_count:
                await send_email(f"Alert: More units have been occupied. Current count: {occupied_count} occupied, {available_count} available in lottery.")

        # Update the previous count after sending the initial or change email
        occupied_previous_count = occupied_count

    except Exception as e:
        await send_email(f"Error occurred: {str(e)}")

    await browser.close()

async def main():
    await send_email("Script started: Monitoring availability changes.")
    while True:
        await check_listings()
        await asyncio.sleep(1800)  # Check every 10 minutes

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

