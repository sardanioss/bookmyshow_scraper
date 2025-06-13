import zendriver as zd
import asyncio
import cloudscraper
import json
import time
from bs4 import BeautifulSoup
import re


def extract_page_cta_formats(json_data):
    try:
        page_cta = json_data.get("synopsisStore", {}).get("synopsisRender", {}).get("bannerWidget", {}).get("pageCta", [])
        
        if not page_cta:
            return {"formats": []}
        
        booking_cta = page_cta[0] if page_cta else {}
        meta = booking_cta.get("meta", {})
        options = meta.get("options", [])
        
        formats = []
        
        for option in options:
            language = option.get("language", "")
            language_formats = option.get("formats", [])
            
            for format_item in language_formats:
                formats.append({
                    "dimension": format_item.get("dimension", ""),
                    "eventCode": format_item.get("eventCode", ""),
                    "language": language
                })
        
        return {"formats": formats}
        
    except Exception as e:
        print(f"Error extracting pageCta formats: {e}")
        return {"formats": []}


def get_movie_name(movie_name: str, session: cloudscraper.CloudScraper) -> dict:
    movie_name = movie_name.replace(" ", "%20")
    url = f"https://in.bookmyshow.com/quickbook-search.bms?q={movie_name}"
    response = session.get(url)
    data = response.json()
    if not data.get("hits"):
        return None

    movie = data["hits"][0]

    return {
        "title": movie.get("TITLE"),
        "group_title": movie.get("GROUP_TITLE"),
        "release_date": movie.get("RDATE"),
        "code": movie.get("CODE"),
        "id": movie.get("ID"),
        "slug": movie.get("SLUG"),
        "poster_url": movie.get("POSTER_URL"),
        "category": movie.get("TYPE_NAME"),
        "status": movie.get("ST"),
        "is_stream": movie.get("IS_STREAM"),
        "is_online": movie.get("IS_ONLINE")
    }


async def verify_showtime_page(page):
    try:
        html = await page.get_content()
        showtime_indicators = [
            "Select Seats",
            "proceed-Qty",
            "bar-btn _primary _full-width _centered"
        ]
        
        for indicator in showtime_indicators:
            if indicator in html:
                return True
        
        return False
    except Exception as e:
        return False


async def click_select_seats_button(page):
    try:
        if not await verify_showtime_page(page):
            return False
        
        current_url = page.url
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                try:
                    select_seats_button = await page.find("Select Seats", timeout=5)
                    if select_seats_button:
                        await select_seats_button.click()
                except Exception as e:
                    try:
                        await page.evaluate("""
                            (function() {
                                const button = document.getElementById('proceed-Qty');
                                if (button) {
                                    button.click();
                                    return true;
                                }
                                return false;
                            })();
                        """)
                    except Exception as js_error:
                        continue
                
                time.sleep(3)
                
                new_url = page.url
                html = await page.get_content()
                
                seat_page_indicators = [
                    "showtime-section",
                    "more-shows",
                    "slick-slide"
                ]
                
                is_seat_page = any(indicator in html for indicator in seat_page_indicators)
                
                if new_url != current_url or is_seat_page:
                    return True
                else:
                    if attempt < max_attempts - 1:
                        time.sleep(2)
                        
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(2)
        
        return False
        
    except Exception as e:
        return False


async def extract_time_slots(page):
    try:
        html = await page.get_content()
        soup = BeautifulSoup(html, "html.parser")
        
        time_slots = []
        
        time_slot_elements = soup.find_all("li", id=True)
        
        for element in time_slot_elements:
            anchor = element.find("a")
            if anchor:
                time_text = anchor.get_text(strip=True).split('\n')[0].strip()
                
                time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM))'
                time_match = re.search(time_pattern, time_text, re.IGNORECASE)
                
                if time_match:
                    clean_time = time_match.group(1).strip()
                    
                    is_hidden = element.get("aria-hidden") == "true"
                    is_active = "_active" in element.get("class", [])
                    element_id = element.get("id")
                    
                    time_slots.append({
                        "time": clean_time,
                        "original_text": time_text,
                        "element_id": element_id,
                        "is_hidden": is_hidden,
                        "is_active": is_active,
                        "element": element
                    })
        
        return time_slots
        
    except Exception as e:
        return []


async def click_next_button(page):
    try:
        next_button = await page.find("Next", timeout=5)
        if next_button:
            await next_button.click()
            time.sleep(2)
            return True
        else:
            return False
    except Exception as e:
        return False


async def count_seat_availability(page):
    try:
        time.sleep(3)
        
        html = await page.get_content()
        soup = BeautifulSoup(html, "html.parser")
        
        seat_table = soup.find("table", class_="setmain")
        if not seat_table:
            return {"available": 0, "blocked": 0, "total": 0}
        
        available_seats = 0
        blocked_seats = 0
        
        available_elements = seat_table.find_all("a", class_="_available")
        available_seats = len(available_elements)
        
        blocked_elements = seat_table.find_all("a", class_="_blocked")
        blocked_seats = len(blocked_elements)
        
        total_seats = available_seats + blocked_seats
        
        return {
            "available": available_seats,
            "blocked": blocked_seats,
            "total": total_seats
        }
        
    except Exception as e:
        return {"available": 0, "blocked": 0, "total": 0}


async def click_time_slot(page, time_slot):
    try:
        if time_slot.get("is_active"):
            time.sleep(1)
            return True
        
        if time_slot.get("element_id"):
            try:
                await page.evaluate(f"""
                    (function() {{
                        const targetElement = document.getElementById('{time_slot['element_id']}');
                        if (targetElement) {{
                            const anchorElement = targetElement.querySelector('a');
                            if (anchorElement) {{
                                anchorElement.click();
                                return true;
                            }} else {{
                                targetElement.click();
                                return true;
                            }}
                        }}
                        return false;
                    }})();
                """)
                time.sleep(3)
                return True
            except Exception as e:
                pass
        
        try:
            html = await page.get_content()
            soup = BeautifulSoup(html, "html.parser")
            showtime_section = soup.find("div", class_="showtime-section")
            
            if showtime_section:
                time_elements = showtime_section.find_all("a", string=lambda text: text and time_slot["time"] in text)
                if time_elements:
                    for elem in time_elements:
                        parent_li = elem.find_parent("li")
                        if parent_li and not ("_active" in parent_li.get("class", [])):
                            element_id = parent_li.get("id")
                            if element_id:
                                await page.evaluate(f"""
                                    (function() {{
                                        const elem = document.getElementById('{element_id}');
                                        if (elem) {{
                                            const anchor = elem.querySelector('a');
                                            if (anchor) {{
                                                anchor.click();
                                                return true;
                                            }}
                                        }}
                                        return false;
                                    }})();
                                """)
                                time.sleep(3)
                                return True
        except Exception as e:
            pass
        
        try:
            time_part = time_slot["time"].split()[0]
            am_pm = time_slot["time"].split()[1] if len(time_slot["time"].split()) > 1 else ""
            
            result = await page.evaluate(f"""
                (function() {{
                    const timeSlots = document.querySelectorAll('.showtime-section li a');
                    for (let i = 0; i < timeSlots.length; i++) {{
                        const slot = timeSlots[i];
                        if (slot.textContent.includes('{time_part}') && slot.textContent.includes('{am_pm}')) {{
                            const parentLi = slot.closest('li');
                            if (parentLi && !parentLi.classList.contains('_active')) {{
                                slot.click();
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }})();
            """)
            
            if result:
                time.sleep(3)
                return True
        except Exception as e:
            pass
        
        try:
            time_element = await page.find(time_slot["time"], timeout=3)
            if time_element:
                await time_element.click()
                time.sleep(3)
                return True
        except Exception as e:
            pass
        
        return False
        
    except Exception as e:
        return False


async def click_back_button(page):
    try:
        try:
            await page.evaluate("fnClCallout()")
            time.sleep(3)
            return True
        except Exception as e:
            pass
        
        try:
            back_element = await page.find("#disback", timeout=5)
            if back_element:
                await back_element.click()
                time.sleep(3)
                return True
        except Exception as e:
            pass
        
        try:
            back_element = await page.find(".st-back-btn", timeout=5)
            if back_element:
                await back_element.click()
                time.sleep(3)
                return True
        except Exception as e:
            pass
        
        try:
            html = await page.get_content()
            soup = BeautifulSoup(html, "html.parser")
            back_elements = soup.find_all(attrs={"onclick": "fnClCallout()"})
            
            if back_elements:
                element_id = back_elements[0].get("id")
                if element_id:
                    await page.evaluate(f"document.getElementById('{element_id}').click()")
                    time.sleep(3)
                    return True
        except Exception as e:
            pass
        
        try:
            await page.evaluate("window.history.back()")
            time.sleep(3)
            return True
        except Exception as e:
            pass
        
        return False
        
    except Exception as e:
        return False


async def get_top_5_cinemas(movie_slug: str, event_code: str, page):
    url = f"https://in.bookmyshow.com/movies/{city}/{movie_slug}/buytickets/{event_code}/"
    await page.get(url)
    time.sleep(3)
    
    html = await page.get_content()
    soup = BeautifulSoup(html, "html.parser")
    
    cinemas = []
    
    cinema_containers = soup.find_all("div", class_="sc-e8nk8f-3 hStBrg")
    
    for i, container in enumerate(cinema_containers[:5]):
        try:
            cinema_name_element = container.find("div", class_="sc-7o7nez-0 hvoTNx")
            cinema_name = cinema_name_element.text.strip() if cinema_name_element else "Unknown Cinema"
            
            first_time_slot = None
            time_slots = container.find_all("div", class_="sc-1vhizuf-2 jIiAgZ")
            if time_slots:
                first_time_slot = time_slots[0].text.strip()
            
            cinema_info = {
                "name": cinema_name,
                "first_time_slot": first_time_slot,
                "position": i + 1
            }
            
            cinemas.append(cinema_info)
            
            if first_time_slot:
                print(f"Processing cinema {i+1}: {cinema_name}")
                
                cinema_name_for_targeting = ' '.join(cinema_name.split()[:3])
                click_success = await click_cinema_time_slot_simple(page, cinema_name_for_targeting, first_time_slot)
                
                if click_success:
                    if await verify_time_slot_page(page):
                        showtime_data = await process_all_time_slots(page, cinema_name)
                        cinema_info["showtime_data"] = showtime_data
                        
                        await page.get(url)
                        time.sleep(5)
                        
                    else:
                        cinema_info["showtime_data"] = {"error": "Failed to reach time slot page"}
                        
                        await page.get(url)
                        time.sleep(3)
                else:
                    cinema_info["showtime_data"] = {"error": "Failed to click first time slot"}
            else:
                cinema_info["showtime_data"] = {"error": "No time slots available"}
            
            time.sleep(2)
            
        except Exception as e:
            try:
                await page.get(url)
                time.sleep(3)
            except:
                pass
            continue
    
    return cinemas


def save_all_cinema_data_to_json(all_formats_data, filename="output.json"):
    try:
        output_data = []
        
        for format_data in all_formats_data:
            format_info = format_data["format_info"]
            cinemas_data = format_data["cinemas"]
            
            format_entry = {
                "movie_type": format_info["dimension"],
                "language": format_info["language"],
                "cinemas": []
            }
            
            for cinema in cinemas_data:
                showtime_data = cinema.get("showtime_data", {})
                
                if "error" in showtime_data or not showtime_data.get("showtimes"):
                    continue
                
                cinema_entry = {
                    "name": cinema["name"],
                    "showtimes": []
                }
                
                for showtime in showtime_data.get("showtimes", []):
                    showtime_entry = {
                        "time": showtime["time"],
                        "available_seats": showtime["available_seats"],
                        "blocked_seats": showtime["blocked_seats"],
                        "total_seats": showtime["total_seats"]
                    }
                    cinema_entry["showtimes"].append(showtime_entry)
                
                if cinema_entry["showtimes"]:
                    format_entry["cinemas"].append(cinema_entry)
            
            if format_entry["cinemas"]:
                output_data.append(format_entry)
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        print(f"Successfully saved all cinema data to {filename}")
        return True
        
    except Exception as e:
        print(f"Error saving cinema data to JSON: {e}")
        return False


async def click_cinema_time_slot_simple(page, cinema_name: str, time_slot: str):
    try:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                result = await page.evaluate(f"""
                    (function() {{
                        const cinemaContainers = document.querySelectorAll('.sc-e8nk8f-3.hStBrg');
                        
                        for (let i = 0; i < cinemaContainers.length; i++) {{
                            const container = cinemaContainers[i];
                            
                            const cinemaNameElement = container.querySelector('.sc-7o7nez-0.hvoTNx');
                            if (cinemaNameElement) {{
                                const containerCinemaName = cinemaNameElement.textContent.trim();
                                
                                if (containerCinemaName.includes('{cinema_name}')) {{
                                    const timeSlots = container.querySelectorAll('.sc-1vhizuf-2.jIiAgZ');
                                    
                                    for (let j = 0; j < timeSlots.length; j++) {{
                                        const slot = timeSlots[j];
                                        const slotText = slot.textContent.trim();
                                        
                                        if (slotText === '{time_slot}') {{
                                            slot.click();
                                            return true;
                                        }}
                                    }}
                                    
                                    return false;
                                }}
                            }}
                        }}
                        
                        return false;
                    }})();
                """)
                
                if result:
                    time.sleep(1)
                    
                    try:
                        continue_button = await page.find("Continue", timeout=2)
                        if continue_button:
                            await continue_button.click()
                            time.sleep(5)
                        else:
                            time.sleep(5)
                    except Exception:
                        time.sleep(5)
                    
                    return True
                else:
                    try:
                        time_element = await page.find(time_slot, timeout=3)
                        if time_element:
                            await time_element.click()
                            time.sleep(1)
                            
                            try:
                                continue_button = await page.find("Continue", timeout=2)
                                if continue_button:
                                    await continue_button.click()
                                    time.sleep(5)
                                else:
                                    time.sleep(5)
                            except Exception:
                                time.sleep(5)
                            
                            return True
                    except Exception as fallback_error:
                        pass
                    
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(2)
        
        return False
        
    except Exception as e:
        return False


async def verify_time_slot_page(page):
    try:
        html = await page.get_content()
        
        time_slot_indicators = [
            "showtime-section",
            "more-shows",
            "slick-slide"
        ]
        
        for indicator in time_slot_indicators:
            if indicator in html:
                return True
        
        return False
        
    except Exception as e:
        return False


async def process_all_time_slots(page, cinema_name):
    try:
        all_time_slots = await extract_time_slots(page)
        if not all_time_slots:
            return {"cinema": cinema_name, "showtimes": [], "error": "No time slots found"}
        
        showtimes_data = []
        processed_times = set()
        
        for i, time_slot in enumerate(all_time_slots):
            if time_slot["time"] in processed_times:
                continue
            
            if time_slot["is_hidden"]:
                await click_next_button(page)
                time.sleep(2)
            
            if time_slot.get("is_active"):
                seat_data = await count_seat_availability(page)
            else:
                if await click_time_slot(page, time_slot):
                    seat_data = await count_seat_availability(page)
                else:
                    continue
            
            showtime_info = {
                "time": time_slot["time"],
                "available_seats": seat_data["available"],
                "blocked_seats": seat_data["blocked"],
                "total_seats": seat_data["total"]
            }
            
            showtimes_data.append(showtime_info)
            processed_times.add(time_slot["time"])
            
            time.sleep(1)
        
        return {
            "cinema": cinema_name,
            "showtimes": showtimes_data,
            "total_showtimes": len(showtimes_data)
        }
        
    except Exception as e:
        return {"cinema": cinema_name, "showtimes": [], "error": str(e)}


async def main(city: str, movie_slug: str, movie_code: str):
    browser = await zd.start(headless=True)
    url = f"https://in.bookmyshow.com/movies/{city}/{movie_slug}/{movie_code}/"
    page = await browser.get(url)
    time.sleep(5)
    html = await page.get_content()
    
    soup = BeautifulSoup(html, "html.parser")
    
    scripts = soup.find_all("script", type="text/javascript")
    target_script = None
    
    for script in scripts:
        if script.string and "window.__INITIAL_STATE__" in script.string:
            target_script = script
            break
    
    if not target_script or not target_script.string:
        print("Could not find script tag with window.__INITIAL_STATE__")
        await browser.stop()
        return
    
    try:
        data = target_script.string
        data = data.split("window.__INITIAL_STATE__ = ")[1]
        end_markers = ["};</script>", "};\n", "};"]
        end_pos = -1
        for marker in end_markers:
            pos = data.find(marker)
            if pos != -1:
                end_pos = pos + 1
                break
        
        if end_pos == -1:
            end_pos = data.find("</script>")
            if end_pos != -1:
                temp_data = data[:end_pos]
                end_pos = temp_data.rfind("}") + 1
        
        if end_pos != -1:
            data = data[:end_pos]
        
        json_data = json.loads(data)
        
        formatted_data = extract_page_cta_formats(json_data)
        
    except (IndexError, json.JSONDecodeError) as e:
        print(f"Error parsing JSON data: {e}")
    
    all_formats_data = []
    
    for format in formatted_data["formats"]:
        cinemas = await get_top_5_cinemas(movie_slug, format["eventCode"], page)
        
        format_data = {
            "format_info": format,
            "cinemas": cinemas
        }
        all_formats_data.append(format_data)
    
    save_all_cinema_data_to_json(all_formats_data, "output.json")
    
    await browser.stop()

if __name__ == "__main__":
    city = "vadodara"
    movie_name = "how to train your dragon"
    session = cloudscraper.create_scraper()
    data = get_movie_name(movie_name, session)
    asyncio.run(main(city, data["slug"], data["id"]))