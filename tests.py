# Framework is AI generated but I told it exactly what asks to test against
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
            ('move', 0, 1, 'ace', 'spades', True)   # Should NOT trigger Illegal: unknown (0)
        ],
        'simple_success': [
            ('seed', 0, 'two', 'hearts'),
            ('move', 0, 1, 'four', 'hearts', True)  # Should succeed
        ],
        'simple_fail': [
            ('seed', 0, 'two', 'hearts'),
            ('move', 0, 2, 'five', 'hearts', False) # Should fail, turn moves to Ben
        ],
        'ask_self': [
            ('seed', 0, 'two', 'hearts'),
            ('move', 0, 0, 'three', 'hearts', True) # Max asks Max (Illegal!)
        ],
        'exhaust_set': [
            ('move', 1, 0, 'two', 'hearts', False),   # Alex asks Max (No). Turn to Max.
            ('move', 0, 1, 'ace', 'spades', False),   # Max asks Alex (No). Turn to Alex.
            ('move', 1, 0, 'three', 'hearts', False), # Alex asks Max (No). Turn to Max.
            ('move', 0, 1, 'ace', 'spades', False),   # Max asks Alex (No). Turn to Alex.
            ('move', 1, 0, 'four', 'hearts', False),  # Alex asks Max (No). Turn to Max.
            ('move', 0, 1, 'ace', 'spades', False),   # Max asks Alex (No). Turn to Alex.
            ('move', 1, 0, 'five', 'hearts', False),  # Alex asks Max (No). Turn to Max.
            ('move', 0, 1, 'ace', 'spades', False),   # Max asks Alex (No). Turn to Alex.
            ('move', 1, 0, 'six', 'hearts', False),   # Alex asks Max (No). Turn to Max.
            ('move', 0, 1, 'ace', 'spades', False),   # Max asks Alex (No). Turn to Alex.
            ('move', 1, 0, 'seven', 'hearts', False), # Alex asks Max (No). Turn to Max.
            # Max is now proven to have no cards in Low Hearts.
            ('move', 1, 0, 'two', 'hearts', True)     # Max asks Alex (Illegal!)
        ],
        'take_set': [
            ('move', 0, 3, 'two', 'hearts', True),
            ('move', 0, 3, 'three', 'hearts', True),
            ('move', 0, 3, 'four', 'hearts', True),
            ('move', 0, 3, 'five', 'hearts', True),
            ('move', 0, 3, 'six', 'hearts', True),
            ('move', 0, 3, 'seven', 'hearts', True)
        ]
    }
