Recommend **2025-09-21**: the 7-day onion hold at Pimpalgaon won in Niphad, Ozar and Sinnar. All three had medium confidence and forecast gain_from_waiting of ₹130 per harvested quintal. Tomato from Manchar, lot_condition=1 (picked 1–2 days ago), returned sell_now.

Evaluated all 32 forecast dates, 2025-08-01 through 2025-11-02, for 96 onion runs. There were 15 holds: 3 wins, 6 losses and 6 unscored. The six unscored holds cannot be called won or lost under the existing backtest rules. Lasalgaon (Vinchur) had a four-day-old last report on 2025-09-24; Solapur had a four-day-old last report on 2025-09-30, so real best_today is unavailable on those dates.

All monetary values below are ₹ per harvested quintal. Decisions used only each as_of_date's forecast slice. Real results use unrounded engine calculations; table values display two decimals. Real today prices never look ahead and must be within confidence.stale_days. Held-sale price lookup checks the target date, then next day, then previous day, except a 1-day hold cannot fall back to the previous day. The recommended 2025-09-28 sale target was missing; the permitted 2025-09-29 report at ₹1300 was used, with costs for the locked 7-day hold.

Ozar missing from data/villages.csv; used user-provided coordinates 20.09, 73.93 through injected road distances. Other requested villages use data/villages.csv.

**Hold runs**

| as_of_date | village | days | mandi | net_per_qtl | net_low | net_high | gain_vs_baseline | gain_from_waiting | confidence | real net | real best_today | result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-09-15 | Niphad | 7 | Lasalgaon | 1295 | 1122 | 1688 | 265 | 84 | medium | 1011.04 | 1210.93 | lost |
| 2025-09-15 | Ozar | 7 | Lasalgaon | 1251 | 1077 | 1643 | 124 | 84 | medium | 966.84 | 1166.73 | lost |
| 2025-09-15 | Sinnar | 7 | Lasalgaon | 1226 | 1053 | 1619 | 319 | 84 | medium | 942.10 | 1142.00 | lost |
| 2025-09-18 | Niphad | 7 | Pimpalgaon | 1227 | 1056 | 1676 | 98 | 88 | medium | 1106.89 | 1138.87 | lost |
| 2025-09-18 | Ozar | 7 | Pimpalgaon | 1240 | 1069 | 1689 | 88 | 88 | medium | 1119.74 | 1151.71 | lost |
| 2025-09-18 | Sinnar | 7 | Pimpalgaon | 1175 | 1003 | 1623 | 417 | 88 | medium | 1054.11 | 1086.09 | lost |
| 2025-09-21 | Niphad | 7 | Pimpalgaon | 1219 | 1048 | 1597 | 164 | 130 | medium | 1204.81 | 1088.87 | won |
| 2025-09-21 | Ozar | 7 | Pimpalgaon | 1231 | 1061 | 1610 | 130 | 130 | medium | 1217.66 | 1101.71 | won |
| 2025-09-21 | Sinnar | 7 | Pimpalgaon | 1166 | 995 | 1545 | 433 | 130 | medium | 1152.03 | 1036.09 | won |
| 2025-09-24 | Niphad | 7 | Pimpalgaon | 1287 | 1067 | 1604 | 238 | 148 | medium | 1155.85 | — | unscored |
| 2025-09-24 | Ozar | 7 | Pimpalgaon | 1300 | 1080 | 1617 | 148 | 148 | medium | 1168.70 | — | unscored |
| 2025-09-24 | Sinnar | 7 | Pimpalgaon | 1234 | 1014 | 1552 | 477 | 148 | medium | 1103.07 | — | unscored |
| 2025-09-30 | Niphad | 7 | Pimpalgaon | 1431 | 1182 | 1759 | 352 | 192 | medium | 1106.89 | — | unscored |
| 2025-09-30 | Ozar | 7 | Pimpalgaon | 1444 | 1195 | 1772 | 192 | 192 | medium | 1119.74 | — | unscored |
| 2025-09-30 | Sinnar | 7 | Pimpalgaon | 1378 | 1130 | 1706 | 651 | 192 | medium | 1054.11 | — | unscored |

**2025-08-10 specifically**

All three villages returned sell_now. Their realized nets equal real best_today; there was no hold to demonstrate.

| as_of_date | village | action | days | mandi | net_per_qtl | net_low | net_high | gain_vs_baseline | gain_from_waiting | confidence | real net | real baseline_today | real best_today |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-10 | Niphad | sell_now | 0 | Pimpalgaon | 1339 | 1339 | 1339 | 90 | 0 | medium | 1338.87 | 1249.21 | 1338.87 |
| 2025-08-10 | Ozar | sell_now | 0 | Pimpalgaon | 1352 | 1352 | 1352 | 0 | 0 | medium | 1351.71 | 1351.71 | 1351.71 |
| 2025-08-10 | Sinnar | sell_now | 0 | Pimpalgaon | 1286 | 1286 | 1286 | 629 | 0 | medium | 1286.09 | 657.49 | 1286.09 |

**Full advise() output: onion, 10 qtl, Niphad, defaults, 2025-09-21**

```json
{
  "action": "hold",
  "days": 7,
  "mandi": "Pimpalgaon",
  "net_per_qtl": 1219,
  "net_low": 1048,
  "net_high": 1597,
  "baseline_today": {
    "mandi": "Lasalgaon (Niphad)",
    "net": 1054
  },
  "best_today": {
    "mandi": "Pimpalgaon",
    "net": 1089
  },
  "gain_vs_baseline": 164,
  "gain_from_mandi": 35,
  "gain_from_waiting": 130,
  "confidence": "medium",
  "break_even_price": 1182,
  "hold_limit_days": 21,
  "hold_success_rate": null,
  "prices_as_of": "2025-09-21",
  "uses_baseline": false,
  "assumptions_default": true,
  "why": {
    "price": 1314,
    "spoilage_loss": 27,
    "transport": 61,
    "storage": 7,
    "fees": 0
  },
  "options": [
    {
      "mandi": "Lasalgaon",
      "distance_km": 19.533524130645375,
      "sell_day": 21,
      "price_low": 1025,
      "price_mid": 1580,
      "price_high": 2366,
      "transport_per_qtl": 59,
      "net_low": 882,
      "net_per_qtl": 1403,
      "net_high": 2141,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Niphad)",
      "distance_km": 0.39610511419276523,
      "sell_day": 21,
      "price_low": 1007,
      "price_mid": 1515,
      "price_high": 2306,
      "transport_per_qtl": 21,
      "net_low": 904,
      "net_per_qtl": 1381,
      "net_high": 2123,
      "flags": []
    },
    {
      "mandi": "Pimpalgaon",
      "distance_km": 20.56688060694187,
      "sell_day": 14,
      "price_low": 1099,
      "price_mid": 1512,
      "price_high": 2144,
      "transport_per_qtl": 61,
      "net_low": 979,
      "net_per_qtl": 1375,
      "net_high": 1981,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Vinchur)",
      "distance_km": 22.308854631431224,
      "sell_day": 21,
      "price_low": 1015,
      "price_mid": 1531,
      "price_high": 2239,
      "transport_per_qtl": 65,
      "net_low": 867,
      "net_per_qtl": 1352,
      "net_high": 2016,
      "flags": []
    },
    {
      "mandi": "Lasalgaon",
      "distance_km": 19.533524130645375,
      "sell_day": 14,
      "price_low": 1035,
      "price_mid": 1480,
      "price_high": 2137,
      "transport_per_qtl": 59,
      "net_low": 919,
      "net_per_qtl": 1346,
      "net_high": 1976,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Vinchur)",
      "distance_km": 22.308854631431224,
      "sell_day": 14,
      "price_low": 1025,
      "price_mid": 1435,
      "price_high": 2017,
      "transport_per_qtl": 65,
      "net_low": 904,
      "net_per_qtl": 1297,
      "net_high": 1855,
      "flags": []
    },
    {
      "mandi": "Pimpalgaon",
      "distance_km": 20.56688060694187,
      "sell_day": 7,
      "price_low": 1140,
      "price_mid": 1314,
      "price_high": 1701,
      "transport_per_qtl": 61,
      "net_low": 1048,
      "net_per_qtl": 1219,
      "net_high": 1597,
      "flags": []
    },
    {
      "mandi": "Lasalgaon",
      "distance_km": 19.533524130645375,
      "sell_day": 7,
      "price_low": 1076,
      "price_mid": 1280,
      "price_high": 1697,
      "transport_per_qtl": 59,
      "net_low": 988,
      "net_per_qtl": 1187,
      "net_high": 1596,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Niphad)",
      "distance_km": 0.39610511419276523,
      "sell_day": 7,
      "price_low": 1059,
      "price_mid": 1233,
      "price_high": 1640,
      "transport_per_qtl": 21,
      "net_low": 1009,
      "net_per_qtl": 1180,
      "net_high": 1578,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Niphad)",
      "distance_km": 0.39610511419276523,
      "sell_day": 3,
      "price_low": 1082,
      "price_mid": 1176,
      "price_high": 1352,
      "transport_per_qtl": 21,
      "net_low": 1048,
      "net_per_qtl": 1142,
      "net_high": 1316,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Vinchur)",
      "distance_km": 22.308854631431224,
      "sell_day": 7,
      "price_low": 1067,
      "price_mid": 1239,
      "price_high": 1602,
      "transport_per_qtl": 65,
      "net_low": 973,
      "net_per_qtl": 1142,
      "net_high": 1497,
      "flags": []
    },
    {
      "mandi": "Pimpalgaon",
      "distance_km": 20.56688060694187,
      "sell_day": 0,
      "price_low": 1150,
      "price_mid": 1150,
      "price_high": 1150,
      "transport_per_qtl": 61,
      "net_low": 1089,
      "net_per_qtl": 1089,
      "net_high": 1089,
      "flags": []
    },
    {
      "mandi": "Lasalgaon (Niphad)",
      "distance_km": 0.39610511419276523,
      "sell_day": 0,
      "price_low": 1075,
      "price_mid": 1075,
      "price_high": 1075,
      "transport_per_qtl": 21,
      "net_low": 1054,
      "net_per_qtl": 1054,
      "net_high": 1054,
      "flags": []
    },
    {
      "mandi": "Lasalgaon",
      "distance_km": 19.533524130645375,
      "sell_day": 0,
      "price_low": 1100,
      "price_mid": 1100,
      "price_high": 1100,
      "transport_per_qtl": 59,
      "net_low": 1041,
      "net_per_qtl": 1041,
      "net_high": 1041,
      "flags": []
    },
    {
      "mandi": "Nasik",
      "distance_km": 44.57716872849424,
      "sell_day": 21,
      "price_low": 762,
      "price_mid": 1222,
      "price_high": 1735,
      "transport_per_qtl": 109,
      "net_low": 585,
      "net_per_qtl": 1017,
      "net_high": 1499,
      "flags": [
        "falling"
      ]
    },
    {
      "mandi": "Lasalgaon (Vinchur)",
      "distance_km": 22.308854631431224,
      "sell_day": 0,
      "price_low": 1080,
      "price_mid": 1080,
      "price_high": 1080,
      "transport_per_qtl": 65,
      "net_low": 1015,
      "net_per_qtl": 1015,
      "net_high": 1015,
      "flags": []
    },
    {
      "mandi": "Nasik",
      "distance_km": 44.57716872849424,
      "sell_day": 14,
      "price_low": 770,
      "price_mid": 1160,
      "price_high": 1593,
      "transport_per_qtl": 109,
      "net_low": 615,
      "net_per_qtl": 989,
      "net_high": 1404,
      "flags": [
        "falling"
      ]
    },
    {
      "mandi": "Nasik",
      "distance_km": 44.57716872849424,
      "sell_day": 7,
      "price_low": 799,
      "price_mid": 993,
      "price_high": 1276,
      "transport_per_qtl": 109,
      "net_low": 666,
      "net_per_qtl": 856,
      "net_high": 1133,
      "flags": [
        "falling"
      ]
    },
    {
      "mandi": "Nasik",
      "distance_km": 44.57716872849424,
      "sell_day": 0,
      "price_low": 825,
      "price_mid": 825,
      "price_high": 825,
      "transport_per_qtl": 109,
      "net_low": 716,
      "net_per_qtl": 716,
      "net_high": 716,
      "flags": [
        "falling"
      ]
    },
    {
      "mandi": "Solapur",
      "distance_km": 427.95654572990435,
      "sell_day": 21,
      "price_low": 984,
      "price_mid": 1509,
      "price_high": 2157,
      "transport_per_qtl": 876,
      "net_low": 27,
      "net_per_qtl": 520,
      "net_high": 1128,
      "flags": []
    },
    {
      "mandi": "Pune",
      "distance_km": 232.062625978684,
      "sell_day": 7,
      "price_low": 869,
      "price_mid": 1031,
      "price_high": 1345,
      "transport_per_qtl": 484,
      "net_low": 360,
      "net_per_qtl": 518,
      "net_high": 826,
      "flags": [
        "falling"
      ]
    },
    {
      "mandi": "Solapur",
      "distance_km": 427.95654572990435,
      "sell_day": 14,
      "price_low": 993,
      "price_mid": 1423,
      "price_high": 1958,
      "transport_per_qtl": 876,
      "net_low": 62,
      "net_per_qtl": 474,
      "net_high": 987,
      "flags": []
    },
    {
      "mandi": "Pune",
      "distance_km": 232.062625978684,
      "sell_day": 0,
      "price_low": 900,
      "price_mid": 900,
      "price_high": 900,
      "transport_per_qtl": 484,
      "net_low": 416,
      "net_per_qtl": 416,
      "net_high": 416,
      "flags": [
        "falling"
      ]
    },
    {
      "mandi": "Solapur",
      "distance_km": 427.95654572990435,
      "sell_day": 7,
      "price_low": 1028,
      "price_mid": 1244,
      "price_high": 1542,
      "transport_per_qtl": 876,
      "net_low": 124,
      "net_per_qtl": 335,
      "net_high": 627,
      "flags": []
    },
    {
      "mandi": "Solapur",
      "distance_km": 427.95654572990435,
      "sell_day": 3,
      "price_low": 1048,
      "price_mid": 1160,
      "price_high": 1301,
      "transport_per_qtl": 876,
      "net_low": 160,
      "net_per_qtl": 271,
      "net_high": 410,
      "flags": []
    },
    {
      "mandi": "Solapur",
      "distance_km": 427.95654572990435,
      "sell_day": 2,
      "price_low": 1049,
      "price_mid": 1136,
      "price_high": 1263,
      "transport_per_qtl": 876,
      "net_low": 165,
      "net_per_qtl": 251,
      "net_high": 378,
      "flags": []
    },
    {
      "mandi": "Solapur",
      "distance_km": 427.95654572990435,
      "sell_day": 0,
      "price_low": 1100,
      "price_mid": 1100,
      "price_high": 1100,
      "transport_per_qtl": 876,
      "net_low": 224,
      "net_per_qtl": 224,
      "net_high": 224,
      "flags": []
    }
  ],
  "notes": []
}
```

Real outcome: net ₹1204.81, nearest-today baseline ₹1054.21, best-today net ₹1088.87. The hold beat real best_today by ₹115.94/qtl.

**Full advise() output: tomato, 10 qtl, Manchar, picked 1–2 days ago, 2025-09-21**

```json
{
  "action": "sell_now",
  "days": 0,
  "mandi": "Pimpalgaon",
  "net_per_qtl": 1597,
  "net_low": 1597,
  "net_high": 1597,
  "baseline_today": {
    "mandi": "Junnar (Narayangaon)",
    "net": 1445
  },
  "best_today": {
    "mandi": "Pimpalgaon",
    "net": 1597
  },
  "gain_vs_baseline": 152,
  "gain_from_mandi": 152,
  "gain_from_waiting": 0,
  "confidence": "medium",
  "break_even_price": null,
  "hold_limit_days": 2,
  "hold_success_rate": null,
  "prices_as_of": "2025-09-21",
  "uses_baseline": true,
  "assumptions_default": true,
  "why": {
    "price": 1955,
    "spoilage_loss": 0,
    "transport": 358,
    "storage": 0,
    "fees": 0
  },
  "options": [
    {
      "mandi": "Pimpalgaon",
      "distance_km": 168.77366315435708,
      "sell_day": 0,
      "price_low": 1955,
      "price_mid": 1955,
      "price_high": 1955,
      "transport_per_qtl": 358,
      "net_low": 1597,
      "net_per_qtl": 1597,
      "net_high": 1597,
      "flags": []
    },
    {
      "mandi": "Junnar (Narayangaon)",
      "distance_km": 17.27684006401325,
      "sell_day": 0,
      "price_low": 1500,
      "price_mid": 1500,
      "price_high": 1500,
      "transport_per_qtl": 55,
      "net_low": 1445,
      "net_per_qtl": 1445,
      "net_high": 1445,
      "flags": []
    },
    {
      "mandi": "Pune (Pimpri)",
      "distance_km": 57.385713968840896,
      "sell_day": 1,
      "price_low": 1325,
      "price_mid": 1605,
      "price_high": 1890,
      "transport_per_qtl": 135,
      "net_low": 1134,
      "net_per_qtl": 1403,
      "net_high": 1677,
      "flags": []
    },
    {
      "mandi": "Pune (Pimpri)",
      "distance_km": 57.385713968840896,
      "sell_day": 0,
      "price_low": 1500,
      "price_mid": 1500,
      "price_high": 1500,
      "transport_per_qtl": 135,
      "net_low": 1365,
      "net_per_qtl": 1365,
      "net_high": 1365,
      "flags": []
    },
    {
      "mandi": "Pune (Pimpri)",
      "distance_km": 57.385713968840896,
      "sell_day": 2,
      "price_low": 1314,
      "price_mid": 1605,
      "price_high": 1932,
      "transport_per_qtl": 135,
      "net_low": 1070,
      "net_per_qtl": 1338,
      "net_high": 1640,
      "flags": []
    },
    {
      "mandi": "Pune",
      "distance_km": 74.86372854351615,
      "sell_day": 0,
      "price_low": 950,
      "price_mid": 950,
      "price_high": 950,
      "transport_per_qtl": 170,
      "net_low": 780,
      "net_per_qtl": 780,
      "net_high": 780,
      "flags": []
    },
    {
      "mandi": "Nasik",
      "distance_km": 145.57121138336936,
      "sell_day": 0,
      "price_low": 1000,
      "price_mid": 1000,
      "price_high": 1000,
      "transport_per_qtl": 311,
      "net_low": 689,
      "net_per_qtl": 689,
      "net_high": 689,
      "flags": []
    }
  ],
  "notes": []
}
```

No data files, configuration or engine logic were changed during the scan. Only analysis outputs under ml/engine/demo_scan were created.
