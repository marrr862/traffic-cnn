"""Shared counting-line validation and direction labels."""
import math


def validate_line(line, width, height):
    if len(line) != 4 or not all(math.isfinite(v) for v in line):
        raise ValueError('Line requires four finite coordinates')
    if not all(0 <= value < (width if i % 2 == 0 else height) for i,value in enumerate(line)):
        raise ValueError('Counting line must lie inside frame')
    if line[:2] == line[2:]:
        raise ValueError('Counting line endpoints must differ')
    return list(line)


def direction_labels(line):
    x1,y1,x2,y2 = line
    if y1 == y2:
        positive,negative = ('Դեպի կադրի ստորին եզր','Դեպի կադրի վերին եզր') if x2 > x1 else ('Դեպի կադրի վերին եզր','Դեպի կադրի ստորին եզր')
    elif x1 == x2:
        positive,negative = ('Դեպի կադրի ձախ եզր','Դեպի կադրի աջ եզր') if y2 > y1 else ('Դեպի կադրի աջ եզր','Դեպի կադրի ձախ եզր')
    else:
        positive,negative = 'Դեպի A→B գծի դրական կողմ','Դեպի A→B գծի բացասական կողմ'
    return {'negative_to_positive':positive,'positive_to_negative':negative}
