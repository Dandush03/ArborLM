# P10-I-S5 engineering report (ADR-0028, engineering part)

Astra review: NOT_PERFORMED. Claude review is not Astra review. No registered run is approved by this text; no label here is a success claim for the project.

## ENGINEERING SSD PERFORMANCE

Each line below is read alone. Every latency, byte count and rate is measured through this harness on this device; ratios and the arithmetic table are analytical.

EQ-A (measured counter against predicted bytes): **BYTES CONFIRMED EXACTLY**
- passes counted: 120 (every pass attempted: those with both counter snapshots, every attempt, and the incomplete ones)

EQ-B (cost of one page, and of a page inside a contiguous request; latencies measured, ratios analytical on measured medians): **CONTIGUOUS REQUEST CHEAPER PER PAGE**
- margin m_t = 0.100 (fixed from R1 and M before the candidate plan); repeats on rho(3): cheaper 5, dearer 0, proportional 0 of 5 (valid repeats 5)
| repeat | c(1) median us | p90 us | p99 us | max us | rho(3) | rho(8) | rho(64) |
|---|---|---|---|---|---|---|---|
| 1 | 73.4 | 100.7 | 119.2 | 2,613.2 | 0.444 | 0.213 | 0.065 |
| 2 | 86.9 | 106.8 | 121.3 | 2,614.8 | 0.377 | 0.206 | 0.055 |
| 3 | 76.8 | 104.4 | 125.1 | 2,684.8 | 0.444 | 0.228 | 0.061 |
| 4 | 74.1 | 82.6 | 122.2 | 2,601.7 | 0.442 | 0.213 | 0.064 |
| 5 | 78.4 | 102.9 | 143.9 | 2,683.0 | 0.430 | 0.223 | 0.062 |
| pooled | 75.8 | 102.7 | 130.0 | 2,684.8 | | | |

EQ-D (descriptive cost table, measured; no ordering, speed-up or monotonicity is registered): **COST TABLE REGISTERED**
| depth k | pages s | pooled median us | median of medians us | range us | CV | pages/s (median) | harness h(k) us | tag |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 75.8 | 76.8 | 73.4 to 86.9 | 6.9% | 11,089 | 2.0 |  |
| 1 | 3 | 99.8 | 98.4 | 97.8 to 102.2 | 2.0% | 27,581 | 2.0 |  |
| 1 | 8 | 136.1 | 140.0 | 125.2 to 143.2 | 6.4% | 50,890 | 2.0 |  |
| 1 | 64 | 304.7 | 303.7 | 300.6 to 310.6 | 1.2% | 184,149 | 2.0 |  |
| 2 | 1 | 90.1 | 89.7 | 85.2 to 96.4 | 4.7% | 17,922 | 3.3 |  |
| 2 | 3 | 101.8 | 106.5 | 94.8 to 108.8 | 6.1% | 48,999 | 3.3 |  |
| 2 | 8 | 135.4 | 135.0 | 129.5 to 145.3 | 4.6% | 90,278 | 3.3 |  |
| 2 | 64 | 343.5 | 332.0 | 318.3 to 358.5 | 4.6% | 303,619 | 3.3 |  |
| 4 | 1 | 93.6 | 95.1 | 84.8 to 96.3 | 5.1% | 28,441 | 8.7 |  |
| 4 | 3 | 110.6 | 111.6 | 104.5 to 114.4 | 3.4% | 83,541 | 8.7 |  |
| 4 | 8 | 140.5 | 143.0 | 131.0 to 151.0 | 6.1% | 153,972 | 8.7 |  |
| 4 | 64 | 363.8 | 357.0 | 341.0 to 369.2 | 3.3% | 462,318 | 8.7 |  |
| 8 | 1 | 92.9 | 94.4 | 85.9 to 95.3 | 4.3% | 51,215 | 26.5 | HARNESS-LIMITED |
| 8 | 3 | 120.4 | 120.6 | 116.6 to 124.5 | 2.7% | 134,858 | 26.5 |  |
| 8 | 8 | 166.5 | 166.1 | 161.7 to 171.4 | 2.2% | 208,373 | 26.5 |  |
| 8 | 64 | 644.9 | 642.0 | 616.2 to 662.1 | 2.8% | 518,161 | 26.5 |  |
| 16 | 1 | 118.2 | 116.5 | 111.2 to 143.3 | 11.0% | 65,314 | 49.7 | HARNESS-LIMITED |
| 16 | 3 | 141.2 | 140.8 | 139.0 to 145.5 | 1.7% | 179,290 | 49.7 | HARNESS-LIMITED |
| 16 | 8 | 219.5 | 218.5 | 211.0 to 222.2 | 2.4% | 251,292 | 49.7 |  |
| 16 | 64 | 1,356.9 | 1,383.5 | 1,249.3 to 1,442.0 | 5.3% | 520,259 | 49.7 |  |
| 32 | 1 | 254.0 | 235.9 | 224.4 to 293.5 | 11.9% | 61,841 | 87.0 | HARNESS-LIMITED |
| 32 | 3 | 279.3 | 265.3 | 237.3 to 326.6 | 12.7% | 175,401 | 87.0 | HARNESS-LIMITED |
| 32 | 8 | 374.2 | 381.7 | 319.0 to 426.9 | 11.4% | 260,099 | 87.0 |  |
| 32 | 64 | 2,995.7 | 2,889.7 | 2,738.1 to 3,032.0 | 3.6% | 509,764 | 87.0 |  |

Per cell and repeat (measured, us): median, p90, p99, maximum, and pages per second.

| depth k | pages s | repeat | median | p90 | p99 | max | pages/s |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 73.4 | 100.7 | 119.2 | 2,613.2 | 11,066 |
| 1 | 1 | 2 | 86.9 | 106.8 | 121.3 | 2,614.8 | 10,130 |
| 1 | 1 | 3 | 76.8 | 104.4 | 125.1 | 2,684.8 | 11,089 |
| 1 | 1 | 4 | 74.1 | 82.6 | 122.2 | 2,601.7 | 12,143 |
| 1 | 1 | 5 | 78.4 | 102.9 | 143.9 | 2,683.0 | 11,096 |
| 1 | 3 | 1 | 97.8 | 124.6 | 168.0 | 281.0 | 29,134 |
| 1 | 3 | 2 | 98.4 | 122.8 | 157.3 | 2,695.1 | 27,581 |
| 1 | 3 | 3 | 102.2 | 120.5 | 146.0 | 2,674.4 | 26,315 |
| 1 | 3 | 4 | 98.3 | 121.0 | 158.5 | 2,738.7 | 27,601 |
| 1 | 3 | 5 | 101.0 | 124.4 | 152.3 | 2,652.0 | 26,237 |
| 1 | 8 | 1 | 125.2 | 145.6 | 197.5 | 2,616.0 | 55,821 |
| 1 | 8 | 2 | 143.2 | 158.4 | 2,214.5 | 2,713.5 | 46,393 |
| 1 | 8 | 3 | 140.0 | 156.1 | 241.4 | 2,697.1 | 50,890 |
| 1 | 8 | 4 | 126.1 | 147.0 | 189.0 | 2,626.5 | 55,795 |
| 1 | 8 | 5 | 140.1 | 161.0 | 2,166.5 | 2,638.7 | 47,436 |
| 1 | 64 | 1 | 303.7 | 324.1 | 2,849.6 | 2,849.6 | 187,327 |
| 1 | 64 | 2 | 304.0 | 330.5 | 2,914.6 | 2,914.6 | 184,058 |
| 1 | 64 | 3 | 300.6 | 348.3 | 2,924.8 | 2,924.8 | 185,271 |
| 1 | 64 | 4 | 303.4 | 320.0 | 2,925.0 | 2,925.0 | 184,149 |
| 1 | 64 | 5 | 310.6 | 331.2 | 2,936.5 | 2,936.5 | 180,535 |
| 2 | 1 | 1 | 87.8 | 106.3 | 135.3 | 2,728.1 | 19,587 |
| 2 | 1 | 2 | 96.4 | 107.0 | 138.0 | 2,637.0 | 18,363 |
| 2 | 1 | 3 | 85.2 | 105.1 | 175.0 | 2,604.5 | 17,922 |
| 2 | 1 | 4 | 91.7 | 106.1 | 167.1 | 2,662.9 | 17,132 |
| 2 | 1 | 5 | 89.7 | 103.3 | 185.1 | 2,701.4 | 17,320 |
| 2 | 3 | 1 | 107.4 | 132.4 | 175.5 | 2,726.8 | 49,389 |
| 2 | 3 | 2 | 98.0 | 112.1 | 162.8 | 2,651.1 | 48,999 |
| 2 | 3 | 3 | 106.5 | 127.3 | 169.6 | 2,695.6 | 46,335 |
| 2 | 3 | 4 | 94.8 | 110.2 | 137.2 | 2,669.2 | 54,387 |
| 2 | 3 | 5 | 108.8 | 128.8 | 184.6 | 2,714.6 | 45,934 |
| 2 | 8 | 1 | 135.0 | 162.2 | 2,704.1 | 2,745.2 | 93,206 |
| 2 | 8 | 2 | 139.7 | 166.9 | 2,720.5 | 2,743.9 | 90,278 |
| 2 | 8 | 3 | 145.3 | 170.7 | 2,731.2 | 2,773.5 | 88,322 |
| 2 | 8 | 4 | 129.5 | 152.0 | 2,676.1 | 2,717.0 | 86,379 |
| 2 | 8 | 5 | 132.6 | 151.7 | 2,723.5 | 2,745.9 | 95,222 |
| 2 | 64 | 1 | 330.7 | 403.8 | 3,087.2 | 3,087.2 | 303,619 |
| 2 | 64 | 2 | 345.3 | 399.3 | 2,959.3 | 2,959.3 | 297,800 |
| 2 | 64 | 3 | 318.3 | 396.8 | 3,000.0 | 3,000.0 | 310,404 |
| 2 | 64 | 4 | 332.0 | 400.6 | 2,922.5 | 2,922.5 | 304,125 |
| 2 | 64 | 5 | 358.5 | 398.4 | 2,996.2 | 2,996.2 | 289,747 |
| 4 | 1 | 1 | 91.7 | 116.9 | 2,130.3 | 2,712.7 | 28,441 |
| 4 | 1 | 2 | 95.5 | 112.9 | 2,141.0 | 2,691.0 | 27,761 |
| 4 | 1 | 3 | 95.1 | 115.2 | 164.4 | 2,722.2 | 32,055 |
| 4 | 1 | 4 | 96.3 | 121.8 | 2,115.8 | 3,869.2 | 25,456 |
| 4 | 1 | 5 | 84.8 | 110.0 | 2,158.2 | 2,644.0 | 30,802 |
| 4 | 3 | 1 | 114.4 | 143.3 | 193.2 | 2,801.0 | 82,281 |
| 4 | 3 | 2 | 112.3 | 140.3 | 2,159.5 | 2,811.4 | 73,195 |
| 4 | 3 | 3 | 111.6 | 135.2 | 231.1 | 2,832.0 | 83,541 |
| 4 | 3 | 4 | 111.2 | 133.6 | 191.6 | 2,756.7 | 86,145 |
| 4 | 3 | 5 | 104.5 | 126.5 | 224.8 | 2,722.5 | 89,004 |
| 4 | 8 | 1 | 132.6 | 168.7 | 2,746.2 | 2,747.7 | 153,972 |
| 4 | 8 | 2 | 144.9 | 182.5 | 2,638.5 | 2,644.2 | 122,193 |
| 4 | 8 | 3 | 151.0 | 193.4 | 385.1 | 401.7 | 195,958 |
| 4 | 8 | 4 | 131.0 | 164.2 | 2,644.4 | 2,649.5 | 158,149 |
| 4 | 8 | 5 | 143.0 | 180.0 | 2,772.8 | 2,796.4 | 145,439 |
| 4 | 64 | 1 | 351.6 | 493.5 | 3,099.2 | 3,099.2 | 472,302 |
| 4 | 64 | 2 | 357.0 | 492.4 | 3,102.8 | 3,102.8 | 460,173 |
| 4 | 64 | 3 | 341.0 | 441.3 | 3,005.3 | 3,005.3 | 488,273 |
| 4 | 64 | 4 | 368.7 | 491.5 | 3,122.5 | 3,122.5 | 462,318 |
| 4 | 64 | 5 | 369.2 | 493.7 | 3,262.0 | 3,262.0 | 453,068 |
| 8 | 1 | 1 | 94.4 | 137.0 | 2,711.0 | 2,747.5 | 50,967 |
| 8 | 1 | 2 | 95.0 | 127.9 | 2,678.3 | 2,770.8 | 51,070 |
| 8 | 1 | 3 | 95.3 | 130.5 | 2,672.1 | 2,743.2 | 51,215 |
| 8 | 1 | 4 | 85.9 | 125.4 | 2,588.5 | 2,658.6 | 54,468 |
| 8 | 1 | 5 | 91.9 | 118.3 | 2,584.5 | 2,664.5 | 53,629 |
| 8 | 3 | 1 | 124.5 | 169.2 | 2,721.5 | 2,761.3 | 129,190 |
| 8 | 3 | 2 | 116.6 | 154.2 | 2,692.5 | 2,788.3 | 134,858 |
| 8 | 3 | 3 | 120.6 | 161.9 | 2,664.0 | 2,688.1 | 132,602 |
| 8 | 3 | 4 | 122.7 | 160.4 | 395.1 | 429.7 | 176,446 |
| 8 | 3 | 5 | 118.0 | 150.1 | 2,673.2 | 2,723.4 | 136,248 |
| 8 | 8 | 1 | 166.7 | 231.8 | 2,734.9 | 2,742.8 | 203,468 |
| 8 | 8 | 2 | 161.7 | 233.7 | 2,746.5 | 2,759.9 | 208,373 |
| 8 | 8 | 3 | 163.5 | 215.7 | 2,725.1 | 2,726.8 | 209,623 |
| 8 | 8 | 4 | 171.4 | 219.3 | 2,833.3 | 2,870.5 | 203,560 |
| 8 | 8 | 5 | 166.1 | 207.9 | 2,772.3 | 2,787.0 | 209,822 |
| 8 | 64 | 1 | 616.2 | 3,038.4 | 3,523.2 | 3,523.2 | 517,992 |
| 8 | 64 | 2 | 655.8 | 2,985.1 | 3,347.9 | 3,347.9 | 518,815 |
| 8 | 64 | 3 | 633.4 | 3,033.7 | 3,399.1 | 3,399.1 | 518,161 |
| 8 | 64 | 4 | 642.0 | 3,067.6 | 3,404.8 | 3,404.8 | 522,382 |
| 8 | 64 | 5 | 662.1 | 3,035.5 | 3,383.0 | 3,383.0 | 509,844 |
| 16 | 1 | 1 | 112.1 | 187.2 | 2,645.5 | 2,672.7 | 67,581 |
| 16 | 1 | 2 | 111.2 | 193.8 | 2,684.4 | 2,714.9 | 67,689 |
| 16 | 1 | 3 | 116.5 | 190.5 | 2,627.5 | 2,673.2 | 65,314 |
| 16 | 1 | 4 | 143.3 | 205.8 | 2,713.1 | 2,766.8 | 61,775 |
| 16 | 1 | 5 | 118.4 | 198.5 | 2,671.2 | 2,732.1 | 64,042 |
| 16 | 3 | 1 | 139.0 | 213.5 | 2,687.7 | 2,709.2 | 179,422 |
| 16 | 3 | 2 | 140.2 | 222.9 | 2,730.6 | 2,864.6 | 177,481 |
| 16 | 3 | 3 | 141.2 | 213.7 | 293.2 | 364.2 | 281,660 |
| 16 | 3 | 4 | 140.8 | 219.7 | 2,756.5 | 2,903.9 | 179,290 |
| 16 | 3 | 5 | 145.5 | 213.0 | 2,757.8 | 2,813.8 | 178,717 |
| 16 | 8 | 1 | 218.5 | 344.0 | 2,878.6 | 2,889.2 | 251,332 |
| 16 | 8 | 2 | 222.2 | 395.5 | 2,761.3 | 2,794.0 | 249,373 |
| 16 | 8 | 3 | 212.8 | 431.0 | 2,811.5 | 2,815.0 | 252,047 |
| 16 | 8 | 4 | 211.0 | 460.3 | 2,806.2 | 2,816.8 | 251,292 |
| 16 | 8 | 5 | 222.0 | 444.5 | 2,689.2 | 2,704.3 | 250,275 |
| 16 | 64 | 1 | 1,336.6 | 3,596.8 | 4,185.5 | 4,185.5 | 520,695 |
| 16 | 64 | 2 | 1,393.7 | 3,657.4 | 4,328.2 | 4,328.2 | 517,588 |
| 16 | 64 | 3 | 1,383.5 | 3,583.0 | 3,906.3 | 3,906.3 | 520,259 |
| 16 | 64 | 4 | 1,249.3 | 1,711.5 | 1,909.2 | 1,909.2 | 730,163 |
| 16 | 64 | 5 | 1,442.0 | 3,481.6 | 3,945.1 | 3,945.1 | 511,726 |
| 32 | 1 | 1 | 235.9 | 636.0 | 2,854.5 | 3,720.2 | 61,841 |
| 32 | 1 | 2 | 224.4 | 597.0 | 2,965.3 | 3,071.5 | 63,968 |
| 32 | 1 | 3 | 293.5 | 627.2 | 2,732.5 | 2,799.6 | 59,474 |
| 32 | 1 | 4 | 229.3 | 625.3 | 2,953.1 | 3,156.8 | 63,842 |
| 32 | 1 | 5 | 269.9 | 671.8 | 2,771.0 | 2,807.1 | 61,504 |
| 32 | 3 | 1 | 265.3 | 651.2 | 2,929.6 | 3,012.9 | 175,401 |
| 32 | 3 | 2 | 292.9 | 804.8 | 2,901.6 | 2,954.2 | 168,443 |
| 32 | 3 | 3 | 237.3 | 722.0 | 2,910.5 | 3,253.9 | 177,177 |
| 32 | 3 | 4 | 326.6 | 836.8 | 2,698.4 | 2,883.5 | 167,878 |
| 32 | 3 | 5 | 255.8 | 623.9 | 2,876.2 | 2,972.2 | 181,674 |
| 32 | 8 | 1 | 381.7 | 2,771.8 | 2,865.8 | 2,868.5 | 260,099 |
| 32 | 8 | 2 | 339.4 | 2,815.3 | 3,034.4 | 3,131.4 | 264,408 |
| 32 | 8 | 3 | 426.9 | 2,770.4 | 2,882.8 | 2,907.2 | 255,224 |
| 32 | 8 | 4 | 319.0 | 2,892.9 | 3,119.2 | 3,176.9 | 265,116 |
| 32 | 8 | 5 | 384.0 | 2,790.0 | 3,365.3 | 3,372.2 | 255,919 |
| 32 | 64 | 1 | 2,912.8 | 4,720.2 | 5,232.9 | 5,232.9 | 514,530 |
| 32 | 64 | 2 | 2,889.7 | 4,802.5 | 5,249.2 | 5,249.2 | 509,152 |
| 32 | 64 | 3 | 2,738.1 | 4,568.3 | 5,002.5 | 5,002.5 | 516,227 |
| 32 | 64 | 4 | 3,032.0 | 4,796.3 | 5,555.0 | 5,555.0 | 509,764 |
| 32 | 64 | 5 | 2,882.2 | 4,844.0 | 5,246.3 | 5,246.3 | 508,165 |

valid repeats: 5 of 5 (E2|r1|a1, E2|r2|a1, E2|r3|a1, E2|r4|a1, E2|r5|a1)

### ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH

ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH. What the page reads of one T-OQ-shaped query (2 branches x 3 pages) would cost under the measured table (analytical: arithmetic on the pooled medians of EQ-D). It excludes the routing computation in RAM, assumes the pages are not cached and assumes rounds add. No query is issued, no branch exists in the file, and nothing in these lines is a measurement of any memory.

ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH
| depth k | as two 3-page requests: rounds x L(depth used, 3) us | as six 1-page requests: rounds x L(depth used, 1) us |
|---|---|---|
| 1 | 2 x L(1, 3) = 199.7 | 6 x L(1, 1) = 454.8 |
| 2 | 1 x L(2, 3) = 101.8 | 3 x L(2, 1) = 270.4 |
| 4 | 1 x L(2, 3) = 101.8 | 2 x L(4, 1) = 187.2 |
| 8 | 1 x L(2, 3) = 101.8 | 2 x L(4, 1) = 187.2 |
| 16 | 1 x L(2, 3) = 101.8 | 2 x L(4, 1) = 187.2 |
| 32 | 1 x L(2, 3) = 101.8 | 2 x L(4, 1) = 187.2 |

### Device record (EC3)

- SMART status: Verified; free space: 653993201664; disk0 driver bytes written since boot: 4212509130752
- lifetime bytes written: NOT READABLE; percentage used: NOT READABLE; temperature: NOT READABLE (they cannot be read without administrator access or a tool install; wear is accounted in the study's own bytes written)
- the study's own bytes written (measured, from the write ledger): 5494538240; charged hours (measured): 0.13
- record files in the run directory (measured; tallied separately and NOT charged to the 10 GB ledger): 28096760 B

### R1's harness figure h(k) (measured on cached pages of the control file; descriptive; E2's own h(k) sets the tag)

| depth k | h(k) median us | status |
|---|---|---|
| 1 | 1.8 | MEASURED |
| 2 | 3.2 | MEASURED |
| 4 | 10.2 | MEASURED |
| 8 | 27.0 | MEASURED |
| 16 | 44.8 | MEASURED |
| 32 | 86.8 | MEASURED |

### What the engineering result can and cannot say

- It can say, for one Apple SSD behind APFS with FileVault, with uncached whole-page requests issued from CPython threads on a synthetic file of 4 GiB that fits in RAM and is only made to behave as if it did not: whether the host-side counter equals the layout's arithmetic; what one page costs at depth 1; whether a page costs less inside a contiguous request; how request latency and pages per second change over six depths and four request sizes, as seen by the host through this harness.
- It says nothing about: any memory, key, query or index (none is in the file); whether a tree or an index is better; the cost of routing or of any computation in RAM; whether storage is needed (the file fits in RAM); warm or hot-page caching; other drives, filesystems or operating systems; an asynchronous or native I/O path; the drive's internal queue; NAND traffic, wear, endurance, sustained writes or updates.

## SCIENTIFIC NEURAL-MEMORY ADVANTAGE

**SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)**

1. No approved learned-address capacity line: Q2 has no approved source; ADR-0024's lane L is unspecified and not approved, so no outcome of the programme can satisfy Q2.
2. The largest licensed cell is about 3 MB: ADR-0023 licenses learned addressing only at tested cell types with load at most L_Q, the largest has 16,384 slots, 16,384 x 192 bytes = 3,145,728 bytes, so Q1, Q2 and Q3 can be true together only if RAM is restricted by construction.

The scientific part is not approved and was not evaluated.
