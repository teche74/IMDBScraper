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
import pandas as pd


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
    genres_data = Counter()

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

            genres_data[movie_data["movie_category"]] += 1

            movies_data.append(movie_data)
        
        except Exception as e:
            print(f"Error processing movie data: {e}")

    return movies_data, directors_films, genres_data

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
file_path = 'csv_files/movies_data-action.csv'
csv_data = load_csv_file(file_path)
if not csv_data:
    print("Error in csv file")
else:
    movies_data, directors_films, genres_data = extract_movie_data(csv_data)

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

    html.Div([
        html.Label("Compare Movies:"),
        dcc.Dropdown(
            id='compare-movies-dropdown',
            options=[{'label': movie['movie_name'], 'value': movie['movie_name']} for movie in movies_data],
            multi=True,
            value=[movies_data[0]['movie_name']] if movies_data else []
        ),
    ], style={'width': '50%', 'margin': 'auto', 'textAlign': 'center', 'padding': '10px'}),

    html.Div(id='overview-analysis', style={'padding': '20px'}),
    
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
    Output('overview-analysis', 'children'),
    Input('compare-movies-dropdown', 'value')
)
def update_overview_analysis(selected_movies):
    if not selected_movies:
        return html.Div()

    overview_data = []
    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie:
            overview_data.append(movie)
    
    return html.Div([
        html.H2("Overview Analysis"),
        html.P(f"Total Movies Selected: {len(overview_data)}"),
        html.P(f"Average Rating: {sum(movie['rating'] for movie in overview_data) / len(overview_data):.2f}"),
        html.P(f"Total User Reviews: {sum(movie['user_reviews'] for movie in overview_data)}"),
        html.P(f"Total Critic Reviews: {sum(movie['critic_reviews'] for movie in overview_data)}")
    ])

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

@app.callback(
    Output('ratings-histogram', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_ratings_histogram(selected_movies):
    if not selected_movies:
        return {}

    fig = go.Figure()

    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie and movie['rating']:
            fig.add_trace(go.Histogram(x=[movie['rating']], name=movie_name, opacity=0.75))

    fig.update_layout(title='Distribution of Ratings', xaxis_title='Rating', yaxis_title='Count', barmode='overlay')
    return fig

@app.callback(
    Output('reviews-analysis', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_reviews_analysis(selected_movies):
    if not selected_movies:
        return {}

    fig = go.Figure()

    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie:
            user_reviews = [movie['user_reviews']]
            critic_reviews = [movie['critic_reviews']]
            fig.add_trace(go.Histogram(x=user_reviews, name=f'User Reviews - {movie_name}', marker_color='blue', opacity=0.75))
            fig.add_trace(go.Histogram(x=critic_reviews, name=f'Critic Reviews - {movie_name}', marker_color='green', opacity=0.75))

    fig.update_layout(title='Distribution of Reviews', xaxis_title='Number of Reviews', yaxis_title='Count', barmode='overlay')
    return fig

@app.callback(
    Output('metascore-histogram', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_metascore_histogram(selected_movies):
    if not selected_movies:
        return {}

    fig = go.Figure()

    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie and movie['metascore']:
            fig.add_trace(go.Histogram(x=[movie['metascore']], name=movie_name, opacity=0.75))

    fig.update_layout(title='Distribution of Metascores', xaxis_title='Metascore', yaxis_title='Count', barmode='overlay')
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
    wordcloud = generate_wordcloud_text(all_reviews)

    buffer = BytesIO()
    wordcloud.to_image().save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f'data:image/png;base64,{image_base64}'

@app.callback(
    Output('sentiment-analysis', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_sentiment_analysis(selected_movies):
    if not selected_movies:
        return {}

    fig = go.Figure()

    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie and movie['user_reviews_data']:
            sentiment_scores = [analyze_sentiment(review['Content']) for review in movie['user_reviews_data']]
            fig.add_trace(go.Histogram(x=sentiment_scores, name=movie_name, opacity=0.75))

    fig.update_layout(title='Distribution of Sentiment Scores', xaxis_title='Sentiment Score', yaxis_title='Count', barmode='overlay')
    return fig

@app.callback(
    Output('film-plot-wordcloud', 'src'),
    Input('compare-movies-dropdown', 'value')
)
def update_film_plot_wordcloud(selected_movies):
    if not selected_movies:
        return ''

    all_plots = " ".join(movie['film_plot'] for movie_name in selected_movies for movie in movies_data if movie['movie_name'] == movie_name)
    wordcloud = generate_wordcloud_text(all_plots)

    buffer = BytesIO()
    wordcloud.to_image().save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f'data:image/png;base64,{image_base64}'

@app.callback(
    Output('directors-films-bar', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_directors_films_bar(selected_movies):
    if not selected_movies:
        return {}

    director_counts = Counter()
    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie:
            for director in movie["directors"]:
                director_counts[director] += 1

    directors = list(director_counts.keys())
    films_count = list(director_counts.values())

    fig = go.Figure(data=[go.Bar(x=directors, y=films_count, marker_color='lightsalmon')])
    fig.update_layout(title='Number of Films per Director', xaxis_title='Director', yaxis_title='Number of Films')
    return fig

@app.callback(
    Output('genre-distribution-pie', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_genre_distribution_pie(selected_movies):
    if not selected_movies:
        return {}

    genre_counts = Counter()
    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie:
            genre_counts[movie["movie_category"]] += 1

    labels = list(genre_counts.keys())
    values = list(genre_counts.values())

    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig.update_layout(title='Distribution of Movie Genres')
    return fig

@app.callback(
    Output('sentiment-analysis-categories', 'figure'),
    Input('compare-movies-dropdown', 'value')
)
def update_sentiment_analysis_categories(selected_movies):
    if not selected_movies:
        return {}

    sentiment_scores = []
    for movie_name in selected_movies:
        movie = next((m for m in movies_data if m['movie_name'] == movie_name), None)
        if movie:
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
