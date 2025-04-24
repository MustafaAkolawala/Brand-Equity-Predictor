from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import csv
import argparse
import os
import csv
import re

class InstagramNoLoginScraper:
    def __init__(self, headless=False):
        """Initialize the Instagram scraper with browser options."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        
        # Use a realistic user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        # List of terms that indicate non-comment elements
        self.non_comment_terms = [
            "load more comments", "view more comments", "log in", "sign up", 
            "reply", "like", "report", "delete", "meta", "privacy", "terms",
            "locations", "api", "help", "jobs", "blog", "about", "follow",
            "following", "followers", "view", "home", "search", "explore",
            "reels", "messages", "notifications", "create", "profile",
            "instagram", "from", "facebook", "data policy", "cookies",
            "suggest", "accounts", "hashtags", "language","hide all replies"
        ]
    
    def handle_cookie_banner(self):
        """Handle the cookie consent banner if it appears."""
        try:
            # Find and click "Decline optional cookies" or similar
            decline_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Decline') or contains(text(), 'Only allow essential cookies')]")
            
            if decline_buttons:
                for button in decline_buttons:
                    try:
                        button.click()
                        print("Clicked decline cookies button")
                        time.sleep(2)
                        return True
                    except:
                        continue
            
            # Try other buttons if the above didn't work
            other_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Accept') or contains(text(), 'Allow') or contains(text(), 'Close')]")
            
            if other_buttons:
                for button in other_buttons:
                    try:
                        button.click()
                        print("Clicked cookie banner button")
                        time.sleep(2)
                        return True
                    except:
                        continue
            
            return False
        except Exception as e:
            print(f"Error handling cookie banner: {e}")
            return False
    
    def handle_login_prompt(self):
        """Handle the login prompt that appears for non-logged in users."""
        try:
            # Try to find and close login prompts or overlays
            close_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Not Now') or contains(text(), 'Cancel') or contains(text(), 'Close')]")
            
            if close_buttons:
                for button in close_buttons:
                    try:
                        button.click()
                        print("Closed login prompt")
                        time.sleep(2)
                        return True
                    except:
                        continue
            
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.click()
                time.sleep(1)
                return True
            except:
                pass
                
            return False
        except Exception as e:
            print(f"Error handling login prompt: {e}")
            return False
    
    def is_likely_comment(self, text):
        """Check if the given text is likely to be a comment rather than UI element."""
        if len(text) < 2:
            return False
            
        text_lower = text.lower()
        for term in self.non_comment_terms:
            if term.lower() in text_lower:
                return False
                
        date_patterns = [
            r'^[A-Z][a-z]+ \d{1,2}, \d{4}$', 
            r'^\d{1,2}[wdhms]$', 
            r'^\d{1,2}:\d{2}$'  
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, text):
                return False
                
        if text.isdigit() or text.replace(',', '').isdigit():
            return False
            
        metadata_indicators = ["original audio", "verified", "sponsored", "paid partnership"]
        for indicator in metadata_indicators:
            if indicator.lower() in text_lower:
                return False
                
        return True

    def get_element_safely(self, elements, index):
        """Safely get an element from a list without index errors."""
        try:
            if 0 <= index < len(elements):
                return elements[index]
            return None
        except:
            return None

    def scrape_comments(self, post_url, max_comments=100):
        """Scrape comments from the given Instagram post URL without logging in."""
        all_comments = []
        comments_seen = set()  
        
        try:
            self.driver.get(post_url)
            print(f"Accessing post URL: {post_url}")
            time.sleep(5)
            self.handle_cookie_banner()
            self.handle_login_prompt
            
            print("Attempting to scrape comments...")
            
            comment_sections = [
                "//ul[contains(@class, 'comment')]",
                "//div[contains(@class, 'comment')]",
                "//div[contains(@role, 'presentation')]//ul",
                "//section//ul",
                "//article//ul"
            ]
            
            comment_section = None
            for section_xpath in comment_sections:
                try:
                    sections = self.driver.find_elements(By.XPATH, section_xpath)
                    if sections:
                        for section in sections:
                            # Check if this section contains at least one comment-like element
                            if section.find_elements(By.TAG_NAME, "li") or section.find_elements(By.TAG_NAME, "div"):
                                comment_section = section
                                print(f"Found potential comments section using XPath: {section_xpath}")
                                break
                except Exception as e:
                    print(f"Error finding comment section with {section_xpath}: {e}")
                    
                if comment_section:
                    break
            
            try:
                view_comments_buttons = self.driver.find_elements(By.XPATH, 
                    "//span[contains(text(), 'View all') or contains(text(), 'View') or contains(text(), 'comments')]")
                for btn in view_comments_buttons:
                    try:
                        btn.click()
                        print("Clicked on 'View all comments' button")
                        time.sleep(3)
                    except:
                        continue
            except:
                print("Either all comments are already showing or post has few comments.")
            
            load_attempt = 0
            prev_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while load_attempt < 10 and len(all_comments) < max_comments:
                self.handle_login_prompt()
                
                try:
                    load_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Load more comments') or contains(text(), 'View more comments') or contains(text(), 'more comment')]")
                    if load_buttons:
                        for button in load_buttons:
                            try:
                                button.click()
                                print("Clicked 'Load more comments' button")
                                time.sleep(3)
                            except:
                                continue
                except:
                    pass
                
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                if comment_section:
                    try:
                        comment_elements = comment_section.find_elements(By.TAG_NAME, "li")
                        
                        for element in comment_elements:
                            try:
                                username_element = None
                                try:
                                    username_elements = element.find_elements(By.TAG_NAME, "h3")
                                    if not username_elements:
                                        username_elements = element.find_elements(By.TAG_NAME, "a")
                                    
                                    username_element = self.get_element_safely(username_elements, 0)
                                except:
                                    pass
                                
                                username = "Unknown"
                                if username_element:
                                    username = username_element.text.strip()
                                
                                span_elements = element.find_elements(By.TAG_NAME, "span")
                                valid_spans = []
                                
                                for span in span_elements:
                                    try:
                                        span_text = span.text.strip()
                                        if span_text and self.is_likely_comment(span_text):
                                            valid_spans.append(span_text)
                                    except StaleElementReferenceException:
                                        continue
                                
                                if valid_spans:
                                    comment_text = max(valid_spans, key=len)
                                    
                                    comment_key = f"{username}:{comment_text}"
                                    
                                    if comment_key not in comments_seen:
                                        all_comments.append({
                                            "comment": comment_text,
                                    
                                        })
                                        comments_seen.add(comment_key)
                                        print(f"Found comment: {username}: {comment_text[:30]}...")
                                        
                                        if len(all_comments) >= max_comments:
                                            break
                            except StaleElementReferenceException:
                                continue
                            except Exception as e:
                                print(f"Error processing comment element: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"Error with comment section strategy: {e}")
                
                if not comment_section or len(all_comments) == 0:
                    try:
                        specific_comment_xpaths = [
                            "//ul//li//div[not(contains(@class, 'time')) and not(contains(@class, 'like')) and not(contains(@class, 'reply'))]//span",
                            "//div[@role='button']//div[not(contains(@role, 'button'))]//span",
                            "//article//ul//li//div//div//div//span"
                        ]
                        
                        for xpath in specific_comment_xpaths:
                            elements = self.driver.find_elements(By.XPATH, xpath)
                            
                            for element in elements:
                                try:
                                    comment_text = element.text.strip()
                                    
                                    if comment_text and self.is_likely_comment(comment_text):
                                        try:
                                            parent_li = element.find_element(By.XPATH, "./ancestor::li")
                                            username_elements = parent_li.find_elements(By.TAG_NAME, "h3")
                                            if username_elements:
                                                username = username_elements[0].text.strip()
                                            else:
                                                username = "Unknown"
                                        except:
                                            username = "Unknown"
                                        
                                        comment_key = f"{username}:{comment_text}"
                                        
                                        if comment_key not in comments_seen:
                                            all_comments.append({
                                                "comment": comment_text,
                               
                                            })
                                            comments_seen.add(comment_key)
                                            print(f"Found comment: {username}: {comment_text[:30]}...")
                                            
                                            if len(all_comments) >= max_comments:
                                                break
                                except StaleElementReferenceException:
                                    continue
                                except Exception as e:
                                    print(f"Error processing element: {str(e)[:100]}...")
                                    continue
                    except Exception as e:
                        print(f"Error with general approach: {e}")
                
                current_height = self.driver.execute_script("return document.body.scrollHeight")
                if current_height == prev_height:
                    load_attempt += 1
                else:
                    load_attempt = 0
                    prev_height = current_height
                
                if len(all_comments) >= max_comments:
                    break
            
            # Print results
            print(f"Successfully scraped {len(all_comments)} comments.")
            
            if len(all_comments) == 0:
                print("\nWARNING: No comments were scraped. This could be because:")
                print("1. The post doesn't have public comments")
                print("2. Instagram is limiting what non-logged-in users can see")
                print("3. Instagram's structure has changed, breaking the scraper")
                print("\nConsider logging in for better results, or try a different post.")
                
            return all_comments
        except Exception as e:
            print(f"Error scraping comments: {e}")
            return all_comments  
    
    def save_to_csv(self, comments, filename="instagram_comments.csv"):
        """Save the scraped comments to a CSV file."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=["comment"])
                writer.writeheader()
                writer.writerows(comments)
            print(f"Comments saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving comments to CSV: {e}")
            return False
    
    def close(self):
        """Close the browser and end the session."""
        self.driver.quit()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import csv
import argparse
import json
import re

class InstagramNoLoginScraper:
    def __init__(self, headless=False):
        """Initialize the Instagram scraper with browser options."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        
        # Use a realistic user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        # List of terms that indicate non-comment elements
        self.non_comment_terms = [
            "load more comments", "view more comments", "log in", "sign up", 
            "reply", "like", "report", "delete", "meta", "privacy", "terms",
            "locations", "api", "help", "jobs", "blog", "about", "follow",
            "following", "followers", "view", "home", "search", "explore",
            "reels", "messages", "notifications", "create", "profile",
            "instagram", "from", "facebook", "data policy", "cookies",
            "suggest", "accounts", "hashtags", "language","hide all replies", "hide replies", "edited"
        ]
    
    def handle_cookie_banner(self):
        """Handle the cookie consent banner if it appears."""
        try:
            # Find and click "Decline optional cookies" or similar
            decline_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Decline') or contains(text(), 'Only allow essential cookies')]")
            
            if decline_buttons:
                for button in decline_buttons:
                    try:
                        button.click()
                        print("Clicked decline cookies button")
                        time.sleep(2)
                        return True
                    except:
                        continue
            
            # Try other buttons if the above didn't work
            other_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Accept') or contains(text(), 'Allow') or contains(text(), 'Close')]")
            
            if other_buttons:
                for button in other_buttons:
                    try:
                        button.click()
                        print("Clicked cookie banner button")
                        time.sleep(2)
                        return True
                    except:
                        continue
            
            return False
        except Exception as e:
            print(f"Error handling cookie banner: {e}")
            return False
    
    def handle_login_prompt(self):
        """Handle the login prompt that appears for non-logged in users."""
        try:
            # Try to find and close login prompts or overlays
            close_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Not Now') or contains(text(), 'Cancel') or contains(text(), 'Close')]")
            
            if close_buttons:
                for button in close_buttons:
                    try:
                        button.click()
                        print("Closed login prompt")
                        time.sleep(2)
                        return True
                    except:
                        continue
            
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.click()
                time.sleep(1)
                return True
            except:
                pass
                
            return False
        except Exception as e:
            print(f"Error handling login prompt: {e}")
            return False
    
    def is_likely_comment(self, text):
        """Check if the given text is likely to be a comment rather than UI element."""
        if len(text) < 2:
            return False
            
        text_lower = text.lower()
        for term in self.non_comment_terms:
            if term.lower() in text_lower:
                return False
                
        date_patterns = [
            r'^[A-Z][a-z]+ \d{1,2}, \d{4}$', 
            r'^\d{1,2}[wdhms]$', 
            r'^\d{1,2}:\d{2}$'  
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, text):
                return False
                
        if text.isdigit() or text.replace(',', '').isdigit():
            return False
            
        metadata_indicators = ["original audio", "verified", "sponsored", "paid partnership"]
        for indicator in metadata_indicators:
            if indicator.lower() in text_lower:
                return False
                
        return True

    def get_element_safely(self, elements, index):
        """Safely get an element from a list without index errors."""
        try:
            if 0 <= index < len(elements):
                return elements[index]
            return None
        except:
            return None

    def scrape_comments(self, post_url, max_comments=100):
        """Scrape comments from the given Instagram post URL without logging in."""
        all_comments = []
        comments_seen = set()  
        
        try:
            self.driver.get(post_url)
            print(f"Accessing post URL: {post_url}")
            time.sleep(5)
            self.handle_cookie_banner()
            self.handle_login_prompt
            
            print("Attempting to scrape comments...")
            
            comment_sections = [
                "//ul[contains(@class, 'comment')]",
                "//div[contains(@class, 'comment')]",
                "//div[contains(@role, 'presentation')]//ul",
                "//section//ul",
                "//article//ul"
            ]
            
            comment_section = None
            for section_xpath in comment_sections:
                try:
                    sections = self.driver.find_elements(By.XPATH, section_xpath)
                    if sections:
                        for section in sections:
                            # Check if this section contains at least one comment-like element
                            if section.find_elements(By.TAG_NAME, "li") or section.find_elements(By.TAG_NAME, "div"):
                                comment_section = section
                                print(f"Found potential comments section using XPath: {section_xpath}")
                                break
                except Exception as e:
                    print(f"Error finding comment section with {section_xpath}: {e}")
                    
                if comment_section:
                    break
            
            try:
                view_comments_buttons = self.driver.find_elements(By.XPATH, 
                    "//span[contains(text(), 'View all') or contains(text(), 'View') or contains(text(), 'comments')]")
                for btn in view_comments_buttons:
                    try:
                        btn.click()
                        print("Clicked on 'View all comments' button")
                        time.sleep(3)
                    except:
                        continue
            except:
                print("Either all comments are already showing or post has few comments.")
            
            load_attempt = 0
            prev_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while load_attempt < 10 and len(all_comments) < max_comments:
                self.handle_login_prompt()
                
                try:
                    load_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Load more comments') or contains(text(), 'View more comments') or contains(text(), 'more comment')]")
                    if load_buttons:
                        for button in load_buttons:
                            try:
                                button.click()
                                print("Clicked 'Load more comments' button")
                                time.sleep(3)
                            except:
                                continue
                except:
                    pass
                
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                if comment_section:
                    try:
                        comment_elements = comment_section.find_elements(By.TAG_NAME, "li")
                        
                        for element in comment_elements:
                            try:
                                username_element = None
                                try:
                                    username_elements = element.find_elements(By.TAG_NAME, "h3")
                                    if not username_elements:
                                        username_elements = element.find_elements(By.TAG_NAME, "a")
                                    
                                    username_element = self.get_element_safely(username_elements, 0)
                                except:
                                    pass
                                
                                username = "Unknown"
                                if username_element:
                                    username = username_element.text.strip()
                                
                                span_elements = element.find_elements(By.TAG_NAME, "span")
                                valid_spans = []
                                
                                for span in span_elements:
                                    try:
                                        span_text = span.text.strip()
                                        if span_text and self.is_likely_comment(span_text):
                                            valid_spans.append(span_text)
                                    except StaleElementReferenceException:
                                        continue
                                
                                if valid_spans:
                                    comment_text = max(valid_spans, key=len)
                                    
                                    comment_key = f"{username}:{comment_text}"
                                    
                                    if comment_key not in comments_seen:
                                        all_comments.append({
                                            "comment": comment_text
                                        })
                                        comments_seen.add(comment_key)
                                        print(f"Found comment: {username}: {comment_text[:30]}...")
                                        
                                        if len(all_comments) >= max_comments:
                                            break
                            except StaleElementReferenceException:
                                continue
                            except Exception as e:
                                print(f"Error processing comment element: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"Error with comment section strategy: {e}")
                
                if not comment_section or len(all_comments) == 0:
                    try:
                        specific_comment_xpaths = [
                            "//ul//li//div[not(contains(@class, 'time')) and not(contains(@class, 'like')) and not(contains(@class, 'reply'))]//span",
                            "//div[@role='button']//div[not(contains(@role, 'button'))]//span",
                            "//article//ul//li//div//div//div//span"
                        ]
                        
                        for xpath in specific_comment_xpaths:
                            elements = self.driver.find_elements(By.XPATH, xpath)
                            
                            for element in elements:
                                try:
                                    comment_text = element.text.strip()
                                    
                                    if comment_text and self.is_likely_comment(comment_text):
                                        try:
                                            parent_li = element.find_element(By.XPATH, "./ancestor::li")
                                            username_elements = parent_li.find_elements(By.TAG_NAME, "h3")
                                            if username_elements:
                                                username = username_elements[0].text.strip()
                                            else:
                                                username = "Unknown"
                                        except:
                                            username = "Unknown"
                                        
                                        comment_key = f"{username}:{comment_text}"
                                        
                                        if comment_key not in comments_seen:
                                            all_comments.append({
                                                "comment": comment_text
                                            })
                                            comments_seen.add(comment_key)
                                            print(f"Found comment: {username}: {comment_text[:30]}...")
                                            
                                            if len(all_comments) >= max_comments:
                                                break
                                except StaleElementReferenceException:
                                    continue
                                except Exception as e:
                                    print(f"Error processing element: {str(e)[:100]}...")
                                    continue
                    except Exception as e:
                        print(f"Error with general approach: {e}")
                
                current_height = self.driver.execute_script("return document.body.scrollHeight")
                if current_height == prev_height:
                    load_attempt += 1
                else:
                    load_attempt = 0
                    prev_height = current_height
                
                if len(all_comments) >= max_comments:
                    break
            
            # Print results
            print(f"Successfully scraped {len(all_comments)} comments.")
            
            if len(all_comments) == 0:
                print("\nWARNING: No comments were scraped.")
            return all_comments
        except Exception as e:
            print(f"Error scraping comments: {e}")
            return all_comments  
    
    def save_to_csv(self, comments, filename="instagram_comments.csv"):
        """Save the scraped comments to a CSV file."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=["comment"])
                writer.writeheader()
                writer.writerows(comments)
            print(f"Comments saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving comments to CSV: {e}")
            return False
    
    def close(self):
        """Close the browser and end the session."""
        self.driver.quit()

def main():

    parser = argparse.ArgumentParser(description='Instagram Comment Scraper (No Login Required) for Multiple Brands')
    parser.add_argument('--base_dir', type=str, required=True, help='Base directory containing brand folders')
    parser.add_argument('--max_comments', type=int, default=100, help='Maximum number of comments to scrape')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()

    scraper = InstagramNoLoginScraper(headless=args.headless)

    # Loop through each brand folder
    for brand_folder in os.listdir(args.base_dir):
        brand_path = os.path.join(args.base_dir, brand_folder)
        if not os.path.isdir(brand_path):
            continue

        post_url_file = os.path.join(brand_path, "post_urls.csv")
        output_file = os.path.join(brand_path, "comments.csv")

        if not os.path.exists(post_url_file):
            print(f" Skipping {brand_folder}: No post_urls.csv found.")
            continue

        print(f"\n Processing brand: {brand_folder}")

        all_comments = []

        with open(post_url_file, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row:
                    continue
                post_url = row[0].strip()
                if not post_url.startswith("http"):
                    continue

                print(f" Scraping: {post_url}")
                try:
                    comments = scraper.scrape_comments(post_url, max_comments=args.max_comments)
                    all_comments.extend(comments)
                except Exception as e:
                    print(f" Error scraping {post_url}: {e}")

        if all_comments:
            with open(output_file, mode="w", newline="", encoding="utf-8") as out_f:
                writer = csv.DictWriter(out_f, fieldnames=["comment"])
                writer.writeheader()
                writer.writerows(all_comments)
            print(f" Saved {len(all_comments)} comments to {output_file}")
        else:
            print(f" No comments found for {brand_folder}")

    scraper.close()

if __name__ == "__main__":
    main()
