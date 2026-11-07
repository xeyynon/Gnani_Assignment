# Prisma alone: 65 synthetic turns, four ways (271 s)

Synthetic Timbre voices; the phone line is a simulation, not Exotel's audio. 

## all turns

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 65 | 3 | 25 | 28% to 51% | 0.348 | 0.544 |
| clean / named | 65 | 0 | 31 | 36% to 60% | 0.331 | 0.538 |
| clean / pipeline | 65 | 0 | 28 | 32% to 55% | 0.338 | 0.544 |
| phone / auto | 65 | 10 | 16 | 16% to 36% | 0.42 | 0.579 |
| phone / named | 65 | 3 | 19 | 20% to 41% | 0.406 | 0.574 |
| phone / pipeline | 65 | 3 | 16 | 16% to 36% | 0.416 | 0.579 |

## short turns (up to 1.6 s)

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 31 | 3 | 14 | 29% to 62% | 0.419 | 0.462 |
| clean / named | 31 | 0 | 19 | 44% to 76% | 0.351 | 0.462 |
| clean / pipeline | 31 | 0 | 17 | 38% to 71% | 0.378 | 0.462 |
| phone / auto | 31 | 6 | 7 | 11% to 40% | 0.595 | 0.654 |
| phone / named | 31 | 2 | 11 | 21% to 53% | 0.541 | 0.654 |
| phone / pipeline | 31 | 2 | 7 | 11% to 40% | 0.595 | 0.654 |

## longer turns

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 34 | 0 | 11 | 19% to 49% | 0.324 | 0.573 |
| clean / named | 34 | 0 | 12 | 22% to 52% | 0.324 | 0.566 |
| clean / pipeline | 34 | 0 | 11 | 19% to 49% | 0.324 | 0.573 |
| phone / auto | 34 | 4 | 9 | 15% to 43% | 0.361 | 0.552 |
| phone / named | 34 | 1 | 8 | 12% to 40% | 0.361 | 0.545 |
| phone / pipeline | 34 | 1 | 9 | 15% to 43% | 0.356 | 0.552 |

## calls in hi-en

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 25 | 0 | 4 | 6% to 35% | 0.723 | 0.839 |
| clean / named | 25 | 0 | 4 | 6% to 35% | 0.723 | 0.839 |
| clean / pipeline | 25 | 0 | 4 | 6% to 35% | 0.723 | 0.839 |
| phone / auto | 25 | 4 | 2 | 2% to 25% | 0.75 | 0.83 |
| phone / named | 25 | 0 | 2 | 2% to 25% | 0.741 | 0.83 |
| phone / pipeline | 25 | 0 | 2 | 2% to 25% | 0.741 | 0.83 |

## calls in hi-IN

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 9 | 0 | 5 | 27% to 81% | 0.143 | None |
| clean / named | 9 | 0 | 6 | 35% to 88% | 0.119 | None |
| clean / pipeline | 9 | 0 | 5 | 27% to 81% | 0.143 | None |
| phone / auto | 9 | 2 | 2 | 6% to 55% | 0.286 | None |
| phone / named | 9 | 1 | 3 | 12% to 65% | 0.262 | None |
| phone / pipeline | 9 | 1 | 2 | 6% to 55% | 0.286 | None |

## calls in te-IN

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 16 | 3 | 5 | 14% to 56% | 0.196 | None |
| clean / named | 16 | 0 | 10 | 39% to 82% | 0.125 | None |
| clean / pipeline | 16 | 0 | 8 | 28% to 72% | 0.143 | None |
| phone / auto | 16 | 2 | 5 | 14% to 56% | 0.268 | None |
| phone / named | 16 | 0 | 7 | 23% to 67% | 0.232 | None |
| phone / pipeline | 16 | 0 | 5 | 14% to 56% | 0.268 | None |

## calls in en-IN

| way | turns | empty | exactly right | 95% interval | WER | T-WER |
|---|---|---|---|---|---|---|
| clean / auto | 15 | 0 | 11 | 48% to 89% | 0.048 | 0.145 |
| clean / named | 15 | 0 | 11 | 48% to 89% | 0.048 | 0.133 |
| clean / pipeline | 15 | 0 | 11 | 48% to 89% | 0.048 | 0.145 |
| phone / auto | 15 | 2 | 7 | 25% to 70% | 0.145 | 0.241 |
| phone / named | 15 | 2 | 7 | 25% to 70% | 0.145 | 0.229 |
| phone / pipeline | 15 | 2 | 7 | 25% to 70% | 0.145 | 0.241 |
