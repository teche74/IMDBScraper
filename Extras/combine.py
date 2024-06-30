import requests
from bs4 import BeautifulSoup
import json
import csv
from flask import Flask, request, jsonify, render_template
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from wordcloud import WordCloud
from textblob import TextBlob
from collections import Counter
import pandas as pd
import ast
import base64
from io import BytesIO

app = Flask(__name__)

# Scraping functions
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
            movie_data = {'movie': movie, 'link': link, 'ImageUrl': movie_image_url }
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

def process_movie(movie_url):
    doc = parse_url(movie_url)
    if not doc:
        return None
    data = {}
    name = get_movie_name(doc)
    year_duration = extract_year_duration(doc)
    rating = extract_rating(doc)
    reviews_info = extract_review_info(doc)
    storyline = get_storyline(doc)
    user_reviews = get_user_reviews(movie_url)
    directors, writers, stars = get_directors_writers_stars(doc)
    details = get_details(doc)
    box_office = get_box_office_details(doc)
    data = {
        "name": name,
        "year_duration": year_duration,
        "rating": rating,
        "review_info": reviews_info,
        "storyline": storyline,
        "user_reviews": user_reviews,
        "directors": directors,
        "writers": writers,
        "stars": stars,
        "details": details,
        "box_office": box_office
    }
    return data

# Flask API
@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    movie_url = data.get('movie_url')
    if not movie_url:
        return jsonify({'error': 'movie_url is required'}), 400

    movie_data = process_movie(movie_url)
    if not movie_data:
        return jsonify({'error': 'Failed to scrape movie data'}), 500

    return jsonify(movie_data)

# Dash App for Visualization
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dashboard/')

dash_app.layout = html.Div([
    dcc.Input(id='input-url', type='text', placeholder='Enter IMDb URL'),
    html.Button('Submit', id='submit-button'),
    html.Div(id='output-data'),
    dcc.Graph(id='wordcloud'),
    dcc.Graph(id='rating-graph'),
    dcc.Graph(id='review-length-graph')
])

def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    image = BytesIO()
    wordcloud.to_image().save(image, format='PNG')
    encoded_image = base64.b64encode(image.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{encoded_image}'

@dash_app.callback(
    [Output('output-data', 'children'),
     Output('wordcloud', 'figure'),
     Output('rating-graph', 'figure'),
     Output('review-length-graph', 'figure')],
    [Input('submit-button', 'n_clicks')],
    [dash.dependencies.State('input-url', 'value')]
)
def update_output(n_clicks, value):
    if not n_clicks or not value:
        return '', {}, {}, {}

    movie_data = process_movie(value)
    if not movie_data:
        return 'Failed to fetch data', {}, {}, {}

    storyline_text = movie_data.get('storyline', 'No storyline found')

    reviews = movie_data.get('user_reviews', [])
    review_texts = ' '.join([review['Content'] for review in reviews])
    wordcloud_image = generate_wordcloud(review_texts)

    ratings = [int(review['Rating']) for review in reviews]
    rating_counts = Counter(ratings)

    review_lengths = [len(review['Content']) for review in reviews]

    wordcloud_figure = {
        'data': [go.Image(z=wordcloud_image)],
        'layout': go.Layout(title='Wordcloud of Reviews')
    }

    rating_figure = {
        'data': [go.Bar(x=list(rating_counts.keys()), y=list(rating_counts.values()))],
        'layout': go.Layout(title='Review Ratings Distribution')
    }

    review_length_figure = {
        'data': [go.Histogram(x=review_lengths)],
        'layout': go.Layout(title='Review Length Distribution')
    }

    return storyline_text, wordcloud_figure, rating_figure, review_length_figure

@app.route('/dashboard')
def render_dashboard():
    return dash_app.index()

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False)
