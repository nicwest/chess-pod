import requests
import random
import boto3
from contextlib import closing
import chess
import chess.pgn
import io
from pydub import AudioSegment
import os

ACCESS_KEY = os.get_env('ACCESS_KEY')
SECRET_KEY = os.get_env('SECRET_KEY')

polly = boto3.client(
    "polly",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name='eu-west-2'

)

LIGHT_SQUARES = chess.SquareSet(chess.BB_LIGHT_SQUARES)
DARK_SQUARES = chess.SquareSet(chess.BB_DARK_SQUARES)


def square_color(s):
    return 'light' if s in LIGHT_SQUARES else 'dark'


colors = '<break time="2s"/>'.join(
    f'{square}<break time="5s" />{color}'
    for square, color in [
        (chess.square_name(s), square_color(s))
        for s in random.sample(chess.SQUARES, 10)
    ]
)


journey_peice = random.choice([chess.KNIGHT, chess.BISHOP])
journey_starting_square = random.choice(chess.SQUARES)
journey_starting_name = chess.square_name(journey_starting_square)
journey_starting_color = square_color(journey_starting_square)
if journey_peice == chess.KNIGHT:
    journey_squares = chess.SQUARES
    journey_peice_name = 'a Knight'
else:
    journey_peice_name = f'the {journey_starting_color} square Bishop'
    if journey_starting_square in LIGHT_SQUARES:
        journey_squares = list(LIGHT_SQUARES)
    else:
        journey_squares = list(DARK_SQUARES)

journey = '<break time="10s" />'.join(
    chess.square_name(s)
    for s in random.sample(journey_squares, 5)
)

target_year = random.randint(1953, 2022)
r = requests.get(
    f'https://explorer.lichess.ovh/masters?since={target_year - 1}&until={target_year + 1}')
game_details = random.choice(r.json()['topGames'])
game_id = game_details["id"]
r = requests.get(
    f'https://explorer.lichess.ovh/masters/pgn/{game_id}')

game = chess.pgn.read_game(io.StringIO(r.text))
print(game)


def fix_name(name):
    n = name.split(',')
    return f'{n[1].strip()} {n[0].strip()}'


game_intro = f"""
    <p>Finally lets walk through the first five  moves of a master game</p>
    <p>Our game today will be between {fix_name(game.headers['White'])} with the white
    pieces and {fix_name(game.headers['Black'])} with the black pieces. The
    game was played in
    {game.headers['Date'][:4]} at the {game.headers['Event']} in
    {game.headers['Site']}</p>
    <p>Remember the goal is to visualise the board after each move.</p>
    <p>Let's begin!</p>
"""

game_moves = []

board = game.board()
for move in list(game.mainline_moves())[:10]:
    san = board.san(move)
    san = san.replace('x', ' takes ')
    san = san.replace('a takes', 'A takes')
    san = san.replace('K', 'King to ')
    san = san.replace('N', 'Knight to ')
    san = san.replace('B', 'Bishop to ')
    san = san.replace('Q', 'Queen to ')
    san = san.replace('R', 'Rook to ')
    san = san.replace('to takes', 'takes')
    san = san.replace('+', ' check!')
    san = san.replace('#', ' checkmate!')
    san = san.replace('O-O-O', 'castles queenside')
    san = san.replace('O-O', 'castles kingside')
    game_moves.append(san)
    board.push(move)


game_moves_text = '<break time="5s" />'.join(game_moves)


bgs = [
    ('sb_signaltonoise.mp3', -28, '"Signal to Noise" by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au'),
    ('sb_aurora.mp3', -20, '"Aurora" by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au'),
    ('HymnToTheDawn.mp3', -25, '"Hymn To The Dawn" by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au')
]


bg, gain, attr = random.choice(bgs)


script = f"""
<speak>
    <p>Welcome to "Unseen Moves," the podcast dedicated to enhancing your chess
    visualization skills.</p>

    <p>In this podcast, we'll embark on a daily journey to help
    you sharpen your ability to visualize the chessboard without actually
    having it in front of you. Visualization is a crucial skill for any chess
    player, enabling you to anticipate and plan your moves ahead of time,
    ultimately leading to better strategic decisions.</p>

    <p>We'll start with a fundamental exercise: naming the color of a square.
    As you practice this skill, you will build up a mental model of the
    chessboard. You will hear the coordinates of a square, and you need
    to supply the color of that square.  Remember it's important to visualise
    the board in your mind, relying on rote memorisation or an algorithm isn't
    going to help you in the long
    run.</p>
    <p>Lets begin!</p>

    <p>
    {colors}
    </p>

    <break time="5s" />

    <p>Well done! Building that mental model of the chess board is the first
    step on the way to better visualisation in chess. Don't worry if you didn't
    get every square perfectly, you will get better with practice!</p>

    <p>For our next exercise you should start by visualising an empty board. We
    will add a single piece at a starting location, then attempt to travel
    around the board,  using only legal moves. You will hear the coordinates
    of a target square. Your job is to find the moves to get the piece to
    that target square, and from there to the next target square, an so
    on.</p>

    <p>Our traveler today will be {journey_peice_name}, starting on the
    {journey_starting_name} square</p>

    <p>Lets begin!</p>

    <p>{journey}</p>

    <break time="10s" />

    <p>Good Job! Visualising how pieces move across the board is vital to
    designing attacks and seeing threats. Don't worry if you didn't hit every
    target perfectly, you will get better with more practise.</p>

   {game_intro}

   <p>{game_moves_text}</p>

   <break time="5s" />

   <p>Amazing work! Keeping track of multiple pieces can be challenging, but as
   you practise you will get better at it!</p>

   <p>The music for this episode was {attr}, Thanks to lichess.org for
   providing sensible APIs to a master games database, text to speach is from
   AWS polly, and a big shout out to the open source devs at python-chess and
   py-dub</p>

   <p>That's all for today. Now get  out there and play some chess!</p>

</speak>
"""

response = polly.synthesize_speech(
    Text=script,
    TextType='ssml',
    LanguageCode='en-GB',
    Engine="neural",
    OutputFormat="mp3",
    VoiceId="Amy"
)

if "AudioStream" in response:
    with closing(response["AudioStream"]) as stream:
        with open('test.mp3', "wb") as file:
            file.write(stream.read())


speech = AudioSegment.from_mp3('test.mp3')
background = AudioSegment.from_mp3(bg)[:len(speech)+10000].fade_out(5000) + gain
silent = AudioSegment.silent(duration=len(speech)+10000)

mix = silent.overlay(background).overlay(speech)
mix.export(f"{game_id}.mp3", format="mp3")
