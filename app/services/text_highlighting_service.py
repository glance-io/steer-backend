from typing import List


class TextHighlightingService:
    def __init__(self, original_text: str, rephrased_text: str):
        self.original_text = original_text
        self.rephrased_text = rephrased_text

    def __longest_common_subsequence(self):
        words1 = self.original_text.lower().split(" ")
        words2 = self.rephrased_text.lower().split(" ")

        matrix = [[0] * (len(words2) + 1) for i in range(len(words1) + 1)]

        # Iterate over the matrix and fill in the values
        for i in range(1, len(words1) + 1):
            for j in range(1, len(words2) + 1):
                if words1[i - 1] == words2[j - 1]:
                    matrix[i][j] = matrix[i - 1][j - 1] + 1
                else:
                    matrix[i][j] = max(matrix[i][j - 1], matrix[i - 1][j])

        # Initialize the LCS list
        lcs_list = []

        # Backtrack to find the LCS
        i = len(words1)
        j = len(words2)
        while i > 0 and j > 0:
            if words1[i - 1] == words2[j - 1]:
                lcs_list.append(words1[i - 1])
                i -= 1
                j -= 1
            elif matrix[i][j - 1] > matrix[i - 1][j]:
                j -= 1
            else:
                i -= 1

        # Reverse the list and return it
        return lcs_list[::-1]

    def create_highlight_list(self):
        common_words = self.__longest_common_subsequence()
        # Split the text into a list of words
        text_words_queue = self.rephrased_text.lower().split(" ")
        common_words_queue = [common_word.lower() for common_word in common_words]

        # Initialize the output list
        output = []

        for word in self.rephrased_text.lower().split(" "):
            if len(common_words_queue) == 0:
                output.append(0)
            elif word == common_words_queue[0]:
                common_words_queue.pop(0)
                text_words_queue.pop(0)
                output.append(1)
            else:
                text_words_queue.pop(0)
                output.append(0)

        # Return the output list
        return output
