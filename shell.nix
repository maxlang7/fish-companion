{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    # 1. System dependencies for audio and graphics handling
    pkgs.flac                # Required by SpeechRecognition
    pkgs.portaudio           # Required for PyAudio
    pkgs.ninja               # Required to build pycairo
    pkgs.pkg-config          # Required to find cairo
    pkgs.cairo               # System library for pycairo
    pkgs.pango               # Often required for graphics/text
    pkgs.gobject-introspection # Required for some python bindings

    # 2. Python environment
    (pkgs.python3.withPackages (ps: with ps; [
      speechrecognition      # The core interface
      pyaudio               # For recording from your microphone
      google-api-python-client # If using Google Cloud (Enterprise)
      openai                # If using OpenAI Whisper API
      requests              # For general API calls
      pip                   # To install cmu-graphics
      setuptools            # Common build dependency
      wheel                 # Common build dependency
    ]))
  ];

  shellHook = ''
    # Create a virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
      python -m venv .venv
    fi
    source .venv/bin/activate

    echo "--- Cloud Speech-to-Text Environment Loaded ---"
    echo "Virtual environment (.venv) activated."
    echo "Run 'pip install cmu-graphics' to install it locally."
  '';
}
