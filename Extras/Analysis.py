import csv
import ast
import base64
from io import BytesIO
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from wordcloud import WordCloud
from textblob import TextBlob
from collections import Counter

# Load CSV file and extract movie data
def load_csv_file(file_path):
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)
        return data
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except Exception as e:
        print(f"Error loading CSV file '{file_path}': {e}")
    return None

def extract_movie_data(csv_data):
    movies_data = []
    directors_films = {}

    for movie in csv_data:
        try:
            movie_data = {
                "movie_name": movie.get("movie_name", "").strip(),
                "movie_imdb_id": movie.get("movie_imdb_id", "").strip(),
                "publish_year": ast.literal_eval(movie.get("YearDuration", "[]"))[0].strip() if movie.get("YearDuration") else "",
                "movie_category": ast.literal_eval(movie.get("YearDuration", "[]"))[1].strip() if movie.get("YearDuration") else "",
                "duration": ast.literal_eval(movie.get("YearDuration", "[]"))[2].strip() if movie.get("YearDuration") else "",
                "rating": float(ast.literal_eval(movie.get("Ratings", "[]"))[0].strip()) if movie.get("Ratings") else 0.0,
                "user_reviews": int(ast.literal_eval(movie.get("ReviewRelatedInfo", "[]"))[0].get("User reviews", "0").strip()) if movie.get("ReviewRelatedInfo") else 0,
                "critic_reviews": int(ast.literal_eval(movie.get("ReviewRelatedInfo", "[]"))[1].get("Critic reviews", "0").strip()) if movie.get("ReviewRelatedInfo") else 0,
                "metascore": int(ast.literal_eval(movie.get("ReviewRelatedInfo", "[]"))[2].get("Metascore", "0").strip()) if movie.get("ReviewRelatedInfo") else 0,
                "film_plot": movie.get("FilmPlot", "").strip(),
                "user_reviews_data": [{"Rating": ur["Rating"].strip(), "Title": ur["Title"].strip(), "Content": ur["Content"].strip()} for ur in ast.literal_eval(movie.get("UserReviews", "[]"))] if movie.get("UserReviews") else [],
                "directors": ast.literal_eval(movie.get("Directors", "[]")) if movie.get("Directors") else []
            }

            for director in movie_data["directors"]:
                director_name = director.strip()
                if director_name not in directors_films:
                    directors_films[director_name] = []
                directors_films[director_name].append(movie_data["movie_name"])

            movies_data.append(movie_data)
        
        except Exception as e:
            print(f"Error processing movie data: {e}")

    return movies_data, directors_films

# Function to generate wordcloud
def generate_wordcloud_text(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    return wordcloud

# Function to generate sentiment analysis
def analyze_sentiment(text):
    analysis = TextBlob(text)
    return analysis.sentiment.polarity

# Initialize Dash app
app = dash.Dash(__name__)

# Load CSV file and extract movie data
file_path = 'csv_files\movies_data.csv'
csv_data = load_csv_file(file_path)
if not csv_data:
    print("Error in csv file")
else:
    movies_data, directors_films = extract_movie_data(csv_data)

# Dash app layout
app.layout = html.Div([
    html.H1("Movie Analysis Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Select a Movie:"),
        dcc.Dropdown(
            id='movie-dropdown',
            options=[{'label': movie['movie_name'], 'value': movie['movie_name']} for movie in movies_data],
            value=movies_data[0]['movie_name'] if movies_data else '',
            clearable=False
        ),
    ], style={'width': '50%', 'margin': 'auto', 'textAlign': 'center', 'padding': '10px'}),

    html.Div(id='movie-info', style={'padding': '20px'}),

    html.Div([
        dcc.Graph(id='ratings-histogram'),
        dcc.Graph(id='reviews-analysis'),
    ], className='row', style={'padding': '20px'}),

    html.Div([
        dcc.Graph(id='metascore-histogram'),
        html.Img(id='wordcloud-image', style={'width': '100%', 'display': 'block', 'margin': 'auto'}),
    ], className='row', style={'padding': '20px'}),

    dcc.Graph(id='sentiment-analysis', style={'padding': '20px'}),

    html.Div([
        html.Div([
            html.H3('Word Cloud of Film Plots', style={'textAlign': 'center'}),
            html.Img(id='film-plot-wordcloud', style={'width': '100%', 'display': 'block', 'margin': 'auto'})
        ], className='six columns'),

        html.Div([
            dcc.Graph(id='directors-films-bar'),
            dcc.Graph(id='genre-distribution-pie'),
        ], className='six columns'),
    ], className='row', style={'padding': '20px'}),

    dcc.Graph(id='sentiment-analysis-categories', style={'padding': '20px'})
])

# Callbacks
@app.callback(
    Output('movie-info', 'children'),
    Input('movie-dropdown', 'value')
)
def update_movie_info(selected_movie):
    if not selected_movie:
        return html.Div()

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie:
        return html.Div()

    return html.Div([
        html.H2(movie['movie_name']),
        html.P(f"Year: {movie['publish_year']}"),
        html.P(f"Category: {movie['movie_category']}"),
        html.P(f"Duration: {movie['duration']}"),
        html.P(f"Rating: {movie['rating']}"),
        html.P(f"Metascore: {movie['metascore']}"),
        html.P(f"Film Plot: {movie['film_plot']}")
    ])

def generate_histogram(x, name, color, nbinsx):
    return go.Histogram(x=x, name=name, marker_color=color, nbinsx=nbinsx)

@app.callback(
    Output('ratings-histogram', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_ratings_histogram(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie or not movie['rating']:
        return {}

    ratings = [movie['rating']]
    fig = go.Figure(data=[go.Histogram(x=ratings, marker_color='#636efa', nbinsx=10)])
    fig.update_layout(title='Distribution of Ratings', xaxis_title='Rating', yaxis_title='Count')
    return fig

@app.callback(
    Output('reviews-analysis', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_reviews_analysis(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie or not movie['user_reviews'] or not movie['critic_reviews']:
        return {}

    user_reviews = [movie['user_reviews']]
    critic_reviews = [movie['critic_reviews']]

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=user_reviews, name='User Reviews', marker_color='blue', nbinsx=10))
    fig.add_trace(go.Histogram(x=critic_reviews, name='Critic Reviews', marker_color='green', nbinsx=10))
    fig.update_layout(barmode='overlay', title='Distribution of Reviews', xaxis_title='Number of Reviews', yaxis_title='Count')
    return fig

@app.callback(
    Output('metascore-histogram', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_metascore_histogram(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie or not movie['metascore']:
        return {}

    metascore = [movie['metascore']]
    fig = go.Figure(data=[go.Histogram(x=metascore, marker_color='purple', nbinsx=10)])
    fig.update_layout(title='Distribution of Metascores', xaxis_title='Metascore', yaxis_title='Count')
    return fig

@app.callback(
    Output('wordcloud-image', 'src'),
    Input('movie-dropdown', 'value')
)
def update_wordcloud_image(selected_movie):
    if not selected_movie:
        return ''

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie:
        return ''

    all_reviews = " ".join(review["Content"] for review in movie["user_reviews_data"])
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_reviews)

    buffer = BytesIO()
    wordcloud.to_image().save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f'data:image/png;base64,{image_base64}'

@app.callback(
    Output('sentiment-analysis', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_sentiment_analysis(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie or not movie['user_reviews_data']:
        return {}

    sentiment_scores = [analyze_sentiment(review['Content']) for review in movie['user_reviews_data']]
    fig = go.Figure(data=[go.Histogram(x=sentiment_scores, marker_color='#FFA500', nbinsx=10)])
    fig.update_layout(title='Distribution of Sentiment Scores', xaxis_title='Sentiment Score', yaxis_title='Count')
    return fig

@app.callback(
    Output('film-plot-wordcloud', 'src'),
    Input('movie-dropdown', 'value')
)
def update_film_plot_wordcloud(selected_movie):
    if not selected_movie:
        return ''

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie:
        return ''

    all_plots = " ".join(movie['film_plot'] for movie in movies_data)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_plots)

    buffer = BytesIO()
    wordcloud.to_image().save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f'data:image/png;base64,{image_base64}'

@app.callback(
    Output('directors-films-bar', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_directors_films_bar(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie:
        return {}

    director_counts = Counter(movie["directors"])
    directors = list(director_counts.keys())
    films_count = list(director_counts.values())

    fig = go.Figure(data=[go.Bar(x=directors, y=films_count, marker_color='lightsalmon')])
    fig.update_layout(title='Number of Films per Director', xaxis_title='Director', yaxis_title='Number of Films')
    return fig

@app.callback(
    Output('genre-distribution-pie', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_genre_distribution_pie(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie:
        return {}

    genre_counts = Counter(movie["movie_category"])
    labels = list(genre_counts.keys())
    values = list(genre_counts.values())

    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig.update_layout(title='Distribution of Movie Genres')
    return fig

@app.callback(
    Output('sentiment-analysis-categories', 'figure'),
    Input('movie-dropdown', 'value')
)
def update_sentiment_analysis_categories(selected_movie):
    if not selected_movie:
        return {}

    movie = next((m for m in movies_data if m['movie_name'] == selected_movie), None)
    if not movie:
        return {}

    sentiment_scores = []
    for review in movie["user_reviews_data"]:
        analysis = TextBlob(review["Content"])
        polarity = analysis.sentiment.polarity

        if polarity > 0:
            sentiment_category = 'Positive'
        elif polarity < 0:
            sentiment_category = 'Negative'
        else:
            sentiment_category = 'Neutral'

        sentiment_scores.append(sentiment_category)

    sentiment_counts = Counter(sentiment_scores)
    labels = list(sentiment_counts.keys())
    values = list(sentiment_counts.values())

    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color='skyblue')])
    fig.update_layout(title='Sentiment Analysis', xaxis_title='Sentiment Category', yaxis_title='Count')
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
