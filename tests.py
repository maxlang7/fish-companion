def get_test_cases():
    """
    Returns a dictionary of test cases.
    Each case is a list of actions:
    ('seed', player_idx, value, suit) or
    ('move', asker_idx, asked_idx, value, suit, got)
    """
    return {
        'duplicate': [
            ('seed', 0, 'three', 'hearts'),
            ('move', 0, 1, 'four', 'hearts', True),
            ('move', 0, 1, 'four', 'hearts', True) # Should trigger Illegal: already has
        ],
        'empty_set': [
            ('move', 0, 1, 'ace', 'spades', True)   # Should trigger Illegal: no cards in set
        ],
        'simple_success': [
            ('seed', 0, 'two', 'hearts'),
            ('move', 0, 1, 'four', 'hearts', True)  # Should succeed
        ],
        'simple_fail': [
            ('seed', 0, 'two', 'hearts'),
            ('move', 0, 2, 'five', 'hearts', False) # Should fail, turn moves to Ben
        ]
    }
