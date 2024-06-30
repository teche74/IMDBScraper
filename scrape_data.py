import requests
from bs4 import BeautifulSoup
import json
import csv

def parse_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  
        content = response.content
        encoding = response.encoding if 'charset' in response.headers.get('content-type', '').lower() else 'utf-8'
        soup = BeautifulSoup(content, 'html.parser', from_encoding=encoding)
        return soup
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error Occurred: \n Code: {e.response.status_code} \n Reason: {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Request Error Occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None



def scrape_movie_image(imdb_id):
    url = f"https://www.imdb.com/title/{imdb_id}/mediaviewer/"
    print(url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        urls = []
        for tag in soup.find_all('img'):
            if 'src' in tag.attrs and tag['src'].startswith('https://'):
                urls.append(tag["src"])         
        
        if not urls:
            return None
        else:
            return urls[0]
    
    except requests.exceptions.RequestException as e:
        print(f"Request Error Occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None

def get_movie_name(body):
    return body.find('span', class_ = 'hero__primary-text').get_text()


def get_movie_name_and_links(doc):
    data = []
    try:
        for container in doc.find_all('a', {'class': 'ipc-title-link-wrapper'}):
            link = container.get('href', '')
            movie = container.find('h3', {'class': 'ipc-title__text'}).get_text(strip=True)
            movie_image_url = scrape_movie_image(link.split('/')[2])
            movie_data = {'movie': movie, 'link': link, 'ImageUrl' : movie_image_url }
            data.append(movie_data)
    except Exception as e:
        print(f"Error extracting movie names and links: {e}")
    return data

def extract_year_duration(body):
    try:
        info = body.find('ul', {'class': 'ipc-inline-list ipc-inline-list--show-dividers sc-d8941411-2 cdJsTz baseAlt'})
        if info:
            result = [s.strip() for s in info.stripped_strings]
            return result
    except Exception as e:
        print(f"Error extracting year and duration: {e}")
    return "N/A"

def extract_rating(body):
    try:
        res = body.find('div', {'data-testid': 'hero-rating-bar__aggregate-rating__score'})
        if res:
            result = [s.strip() for s in res.stripped_strings]
            return result
    except Exception as e:
        print(f"Error extracting rating: {e}")
    return "No rating found"

def extract_review_info(movie_body):
    store = []
    try:
        reviews = movie_body.find_all('span', {'class': 'three-Elements'})
        if reviews:
            for data in reviews:
                header = data.find('span', class_='label').get_text(strip=True)
                score = data.find('span', class_='score').get_text(strip=True)
                store.append({header: score})
    except Exception as e:
        print(f"Error extracting review info: {e}")
    return store

def get_storyline(movie_body):
    text = movie_body.find('div',{'class': 'ipc-html-content-inner-div'})
    if text:
        story = ' '.join([s.strip() for s in text.stripped_strings])
        return story
    else:
        return "No storyline found"
        # return " "
    
def get_user_reviews(url):
    user_review_url = f"https://www.imdb.com/title/{url.split('/')[-2]}/reviews?spoiler=hide&sort=curated&dir=desc&ratingFilter=0"
    review_body = parse_url(user_review_url)
    reviews = []

    if review_body:
        try:
            for each in review_body.find_all('div', class_='review-container'):
                rating_elem = each.find('span', class_="point-scale")
                rating = rating_elem.find_previous_sibling('span').text.strip() if rating_elem else "0"
                title = each.find('a', class_='title').text.strip()
                review_content = each.find('div', class_='content').text.strip()
                reviews.append({"Rating": rating, "Title": title, "Content": review_content})
        except Exception as e:
            print(f"Error extracting user reviews: {e}")
    return reviews

def get_directors_writers_stars(body):
    Directors = []
    Writers = []
    Stars = []
    section = body.find('ul' , class_ = 'ipc-metadata-list ipc-metadata-list--dividers-all title-pc-list ipc-metadata-list--baseAlt')
    
    for dir_name in section.find_all('li' , class_ = 'ipc-metadata-list__item')[0].strings:
        if dir_name != 'Directors' :
            Directors.append(dir_name)

    for writer_name in section.find_all('li' , class_ = 'ipc-metadata-list__item')[1].strings:
        if writer_name != 'Writers' :
            Writers.append(writer_name)

    for star_name in section.find_all('li' , class_ = 'ipc-metadata-list__item')[2].strings:
        if star_name !=  'Stars':
            Stars.append(star_name)

    return Directors,Writers,Stars

def get_details(body):
    details = body.find('section', {'data-testid': 'Details'})
    if not details:
        return {}

    release_date = 'N/A'
    origin_country = 'N/A'
    language = 'N/A'

    try:
        release_date = details.find_all('li')[1].text
    except (IndexError, AttributeError):
        pass

    try:
        origin_country = details.find_all('li')[3].text
    except (IndexError, AttributeError):
        pass

    try:
        language = details.find_all('li')[7].text
    except (IndexError, AttributeError):
        pass

    info = {
        'Release-Date': release_date,
        'Country-Origin': origin_country,
        'Language': language
    }

    return info

def get_box_office_details(body):
    data = {}
    box_office_body = body.find('section', {'data-testid': 'BoxOffice'})
    if not box_office_body:
        return data

    try:
        budget_text = box_office_body.find_all('li')[0].get_text()
        data['Budget'] = '$' + budget_text.split('$')[1]
    except (IndexError, AttributeError, IndexError):
        data['Budget'] = 'N/A'

    try:
        revenue_text = box_office_body.find_all('li')[2].get_text()
        key = revenue_text.split('$')[0]
        value = '$' + revenue_text.split('$')[1]
        data[key] = value
    except (IndexError, AttributeError, IndexError):
        pass

    try:
        text = box_office_body.find_all('li')[4].get_text()
        dollar_index = text.find('$')
        date_index = next(i for i in range(dollar_index + 1, len(text)) if text[i].isalpha())
        location = text[:dollar_index]
        collections = text[dollar_index:date_index]
        date = text[date_index:]
        data[location] = {'Collection': collections, 'Date': date}
    except (IndexError, AttributeError, StopIteration):
        pass

    try:
        other_revenue_text = box_office_body.find_all('li')[7].get_text()
        key = other_revenue_text.split('$')[0]
        value = '$' + other_revenue_text.split('$')[1]
        data[key] = value
    except (IndexError, AttributeError, IndexError):
        pass

    return data


def get_movie_info(link):
    template = f"https://www.imdb.com{link}"
    print(template)
    movie_body = parse_url(template)
    if movie_body is None:
        print(f"Failed to retrieve data for {template}")
        return None

    try:
        movie_name = get_movie_name(movie_body)
        year_duration = extract_year_duration(movie_body)
        ratings = extract_rating(movie_body)
        review_related_info = extract_review_info(movie_body)
        film_plot = get_storyline(movie_body)
        user_reviews = get_user_reviews(link)
        Directors, Writers, Stars = get_directors_writers_stars(movie_body)
        details_section = get_details(movie_body)
        box_office_details = get_box_office_details(movie_body)

        movie_info = {
            "movie_name" :  movie_name,
            "movie_imdb_id": link,
            "YearDuration": year_duration,
            "Ratings": ratings,
            "ReviewRelatedInfo": review_related_info,
            "FilmPlot": film_plot,
            "UserReviews": user_reviews,
            "Directors": Directors,
            "Writers": Writers,
            "Stars": Stars,
            "Details": details_section,
            "BoxOfficeDetails": box_office_details
        }
        return movie_info
    except Exception as e:
        print(f"Error extracting movie info for {link}: {e}")
        return None


def main():
    genre = input("Enter Genre: ")

    url = f"https://www.imdb.com/search/title/?genres={genre}&title_type=feature"

    doc = parse_url(url)
    if doc is None:
        print("Failed to retrieve the main search page. Exiting.")
        return

    name_link_list = get_movie_name_and_links(doc)
    if not name_link_list:
        print("No movies found for the specified genre. Exiting.")
        return

    data_list = []
    print("Processing movies...")
    
    for i, item in enumerate(name_link_list[:20], start=1):
        try:
            print(f"Processing Movie {i}: {item['movie']}")
            movie_info = get_movie_info(item['link'])
            movie_info["name"] = item['movie']
            
            if movie_info:
                data_list.append(movie_info)
        except Exception as e:
            print(f"Error processing movie {item['movie']}: {e}")
        if len(data_list) >= 20:
            break

    if not data_list:
        print("No movie data collected. Exiting.")
        return

    json_filename = f"data_collect/movie_category-{genre}.json"
    csv_filename = f"csv_files/movies_data-{genre}.csv"

    try:
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump(data_list, json_file, ensure_ascii=False, indent=4)
        print(f"JSON data saved to {json_filename}")
    except Exception as e:
        print(f"Error saving JSON data: {e}")

    try:
        keys = data_list[0].keys()
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
            dict_writer = csv.DictWriter(csv_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data_list)
        print(f"CSV data saved to {csv_filename}")
    except Exception as e:
        print(f"Error saving CSV data: {e}")

    print("Data collection successful.")

if __name__ == "__main__":
    main()