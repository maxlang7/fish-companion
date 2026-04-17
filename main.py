from cmu_graphics import *
import threading
import speech_recognition as sr
"""
Required Libraries:
- cmu_graphics
- threading
- speech_recognition
- openai

Setup an openAI key

"""
# Mostly AI b/c I didn't know how to do the listening
def start_listening(app):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)

    while app.isListening:
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=2)

            text = recognizer.recognize_openai(audio, model="gpt-4o-mini-transcribe").lower()
            print(f"Heard: {text}")

            # Me
            for suit in app.suits:
                if suit in text:
                    print('suit')
                    for value in app.values:
                        if value in text:
                            # .capitalize suggested by AI
                            app.asks.append(f'{value.capitalize()} of {suit.capitalize()}')
                            print(app.asks)

        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            print(f"Error: {e}")

def onAppStart(app):
    app.asks=[]
    app.stepsPerSecond = 10
    app.isListening=True
    # Not plural so "four diamond" works ok
    app.suits = ['heart', 'diamond', 'club', 'spade']
    app.values = ['ace', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'jack', 'queen', 'king']
    # Done by AI
    # Start the listening thread
    app.thread = threading.Thread(target=start_listening, args=(app,), daemon=True)
    app.thread.start()

def redrawAll(app):
    drawLabel("Asks:", 200, 50, size=20, bold=True)
    if len(app.asks)>0:
        drawLabel(app.asks[-1], 200, 200, size=16)

def onStep(app):
    pass

def main():
    runApp(width=400, height=400)

if __name__ == '__main__':
    main()
