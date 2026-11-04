from csbench.intervals import intersect, intersection_lines, length, merge, total_lines


def test_merge_overlapping_and_adjacent():
    assert merge([(5, 7), (1, 3), (4, 4), (10, 12)]) == [(1, 7), (10, 12)]
    assert merge([]) == []


def test_length_and_intersect():
    assert length([(1, 3), (2, 5)]) == 5
    assert intersect([(1, 10)], [(5, 6), (9, 20)]) == [(5, 6), (9, 10)]
    assert intersect([(1, 2)], [(3, 4)]) == []


def test_by_file_totals():
    a = {"x.py": [(1, 10)], "y.py": [(1, 1)]}
    b = {"x.py": [(8, 12)], "z.py": [(1, 5)]}
    assert total_lines(a) == 11
    assert intersection_lines(a, b) == 3
