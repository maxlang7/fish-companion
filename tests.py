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
        'exhaust_set': [
            # Max starts with nothing in his set, we need to systematically prove he has NOTHING.
            # Low Hearts: two, three, four, five, six, seven
            # Alex (1) asks Max (0) for each one, Max says no.
            # Turn order: 1->0 (fail) -> Turn goes to 0. 0->1 (fail) -> Turn to 1.
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
            ('move', 0, 1, 'two', 'hearts', True)     # Max asks Alex (Illegal!)
        ]
    }
