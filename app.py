from flask import Flask, request, jsonify, render_template
from scrape_data import parse_url, get_movie_name_and_links, get_movie_info

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/movies', methods=['POST'])
def movies():
    genre = request.form.get('genre')
    if not genre:
        return jsonify({'error': 'Genre parameter is required'}), 400

    url = f"https://www.imdb.com/search/title/?genres={genre}&title_type=feature"
    doc = parse_url(url)

    if not doc:
        return jsonify({'error': 'Failed to fetch data from IMDb'}), 500

    name_link_list = get_movie_name_and_links(doc)

    if not name_link_list:
        return jsonify({'error': 'No movies found for the specified genre'}), 404

    data_list = [{'movie': item['movie'], 'link': item['link'], 'ImageUrl': item['ImageUrl']} for item in name_link_list]
    return jsonify(data_list)

@app.route('/movie-details', methods=['POST'])
def movie_details():
    link = request.form.get('link')
    if not link:
        return jsonify({'error': 'Movie link parameter is required'}), 400

    movie_info = get_movie_info(link)
    if not movie_info:
        return jsonify({'error': 'Failed to fetch movie details'}), 500

    return jsonify(movie_info)

if __name__ == "__main__":
    app.run(debug=True)