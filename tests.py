import unittest
from main import getUserInput, additionalQuestion
from main import userFeedback, sendApiRequest, process_response
from main import modify_database
from unittest.mock import patch, MagicMock
import pandas as pd


class TestMediaRecommendations(unittest.TestCase):

    # GetUserInput
    def test_getUserInput(self):
        with patch('builtins.input', side_effect=['Batman', 'S']):
            choices = getUserInput()
            self.assertEqual(choices, ['Batman'])

    def test_getError(self):
        with patch('builtins.input', side_effect=['S', 'Batman', 'S']):
            choices = getUserInput()
            self.assertEqual(choices, ['Batman'])

    def test_getSixInputs(self):
        with patch('builtins.input', side_effect=[
              'Superman', 'Batman', 'Spiderman', 'Hulk',
              'Wonder Woman', 'Green Lantern']):
            choices = getUserInput()
            self.assertEqual(choices, ['Superman', 'Batman',
                                       'Spiderman', 'Hulk', 'Wonder Woman'])

    # additionalQuestion
    @patch('builtins.input', side_effect=['Sci-Fi'])
    def test_additionalQuestion(self, mock_input):
        preferences = additionalQuestion()
        self.assertEqual(preferences, 'Sci-Fi')

    @patch('builtins.input', side_effect=[''])
    def test_additionalQuestion(self, mock_input):
        preferences = additionalQuestion()
        self.assertEqual(preferences, '')

    # userFeedback
    @patch('builtins.input', side_effect=['Y'])
    def test_userFeedback_positive(self, x):
        feedback = userFeedback()
        self.assertEqual(feedback, '')

    @patch('builtins.input', side_effect=['N', 'Some feedback'])
    def test_userFeedback_negative(self, x):
        feedback = userFeedback()
        self.assertEqual(feedback, 'Some feedback')

    @patch('builtins.input', side_effect=['X', 'Y'])
    def test_userFeedback_negative(self, x):
        feedback = userFeedback()
        self.assertEqual(feedback, '')

    # process_response
    def test_process_response(self):
        formatted_data = {'recommendations': [{
             'title': 'Movie1',
             'genre': 'Action',
             'rating': 8.5,
             'release date': '2020-01-01'
             }
          ]
        }
        recommendations = process_response(formatted_data)
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]['title'], 'Movie1')

    # modify_database
    @patch('pandas.DataFrame.to_sql')
    def test_modify_database(self, MockDataFrame):
        recommendations = [{
            'title': 'Movie1',
            'genre': 'Action', 'rating': 8.5,
            'releaseDate': '2020-01-01'
            }
        ]
        modify_database(recommendations)
        MockDataFrame.assert_called_once()

    # API


if __name__ == '__main__':
    unittest.main()
