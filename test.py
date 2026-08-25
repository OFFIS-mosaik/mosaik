def lengthOfLongestSubstring(s: str) -> int:
    chars_in_sub = []
    max_sub_len = 0
    curr_index = 0
    str_in_progress = True
    while str_in_progress:
        for index, char in enumerate(s[curr_index:], start=curr_index):
            if max_sub_len >= len(s) - curr_index:
                return max_sub_len
            if char not in chars_in_sub:
                print(char)
                chars_in_sub.append(char)
            else:
                curr_index = curr_index + chars_in_sub.index(char) + 1
                print(curr_index)
                print(chars_in_sub)
                if max_sub_len < len(chars_in_sub):
                    max_sub_len = len(chars_in_sub)
                chars_in_sub.clear()
                break
    return max_sub_len

s= "bbbbbb"
print(lengthOfLongestSubstring(s))