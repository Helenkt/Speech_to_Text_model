# Backend: rubric, du lieu gan nhan va kiem thu chat luong

## Pham vi ban 2026-10-17

Chi thay doi backend. Khong sua giao dien, khong doi trong so Transformer,
khong tu tai model moi, khong nhap kien thuc mon hoc tu Internet.
Ngan hang cau hoi va ban ghi sinh vien hien co khong bi viet lai.
Hai bang moi duoc tao khi ung dung khoi dong: `rubric_revisions`, `grading_labels`.
Can sao luu database theo quy trinh thong thuong truoc khi trien khai.

## 1. Rubric nguyen tu co phien ban

- Moi tieu chi co ID, mot phat bieu can danh gia, trong so va trich dan nguon.
- Nguon chi duoc la `reference_answer` hoac `key_points` cua cau hoi hien tai.
- Hash nguon ngan dung nham rubric khi ngan hang cau hoi thay doi.
- He thong kiem tra trung ID, trung phat bieu, trong so, trich dan va phien ban.
- Canh bao phat bieu qua ngan hoac co kha nang chua nhieu yeu cau. Day la
  canh bao theo quy tac, KHONG phai ket luan rubric sai.
- Trich dan dung nguon khong tu dong chung minh phat bieu dung ve ngu nghia.
  Giang vien phai xac nhan y nghia, tinh nguyen tu va trong so khi publish.
- V3 dung diem nhi phan cho tung y. Neu model chi xac nhan duoc mot phan,
  y do la `unresolved`, khong tu gan nua diem. Muon tinh diem tung phan thi
  tach thanh nhieu tieu chi ro rang voi trong so rieng.
- De thi khoa rubric luc tao de; luyen tap khoa rubric luc chon cau hoi.
  Publish ban moi khong sua de thi, cau dang tra loi hay ket qua cu.
- Cau hoi chua co V3 da duyet van dung rubric cu; khong tu duyet hang loat.

API chi danh cho giang vien:

| API | Muc dich |
|---|---|
| `GET /api/teacher/rubrics/{question_uid}` | Ban nhap, canh bao, lich su revision |
| `POST /api/teacher/rubrics/{question_uid}/publish` | Luu revision co xac nhan giang vien |

Payload publish gom `contract` tu API GET, sau khi sua tung criterion, va
`attestation` ghi ro da kiem tra nguon, y nghia, trong so. Khong cho client
tu khai `approved_by`; server lay tai khoan giang vien dang dang nhap.
Khong gui dap an, rubric hay nhan giang vien qua API cau hoi cua sinh vien.

## 2. Thu thap nhan that, khong dung AI lam dap an chuan

| API | Muc dich |
|---|---|
| `GET /api/teacher/answers/{answer_id}/labeling-task?transcript_source=original` | Lay transcript va rubric, KHONG kem diem AI |
| `POST /api/teacher/answers/{answer_id}/point-labels` | Luu nhan tung y kem trich dan nguyen van |
| `GET /api/teacher/quality/corpus` | Xuat cac nhan moi nhat cua tung nguoi cham |
| `GET /api/teacher/quality/triage?limit=1000` | Gom nhom bai can xac minh va mau kiem tra |

Nhan can co du moi point dung mot lan: `met`, `partial` (chi rubric cu),
`missing`, `contradicted`. `missing` khong co trich dan; cac trang thai con
lai phai dan dung doan trong transcript. API nhan yeu cau hai hash lay tu
labeling-task, khong chap nhan nhan cho transcript/rubric da thay doi.

`annotation_mode=independent` la TUYEN BO cua giang vien da cham doc lap;
backend khong the chung minh nguoi cham chua tung xem diem AI o noi khac.
`assisted` danh dau nhan co tham khao AI. Thao tac "chap nhan diem AI" trong
quy trinh cham thi cu KHONG tu tao nhan doc lap. Gan nhan khong doi diem
cuoi; muon cham lai bai thi van dung API cham lai va lich su cu.

Moi lan gan nhan tao dong lich su moi. Export chi lay ban moi nhat cua moi
nguoi cham; nhan cua transcript cu sau khi strong STT doi se bi loai.
Neu hai giang vien bat dong thi bao cao de rieng, khong tu chon mot nguoi
lam dung. Xoa bai thi se xoa nhan lien quan theo khoa ngoai.

Corpus khong xuat file am thanh, duong dan, ten hay email sinh vien. Tuy
nhien NOI DUNG CAU TRA LOI van co the chua du lieu ca nhan. Chi luu noi duoc
phep. Ma nguoi hoc/nguoi cham chi on dinh trong MOT lan export; khong tron
nhieu lan export roi mac dinh cac ma co cung danh tinh.

Triage tach canh bao STT, ngu nghia chua xac minh, bat dong model va quyet
dinh giang vien. Gom theo hash rubric + point + nguyen nhan; lay mau khoang
10% bai khong bi gan co bang hash on dinh. Triage KHONG tu doi diem, giam
nguong tin cay hay tu sua rubric. Viec nghe voice, nghe nhieu lan va cham
lai bat ky bai nao van giu nguyen.

## 3. Quy trinh do chat luong truoc khi fine-tune tiep

1. Thu bai am thanh that; giang vien gan nhan tung y va bang chung.
2. Trong mot corpus duy nhat, chia `train`, `validation`, `blind_test` theo
   ca cau hoi, nguoi hoc va ban tra loi trung lap. Khong chia ngau nhien
   tung dong. Cung cau hoi hay nguoi hoc xuat hien o nhieu split se bi bao
   leakage; co the can thu rieng nhom sinh vien/cau hoi moi de tao blind test.
3. Co mot tap con duoc it nhat hai giang vien cham doc lap. Bat dong can
   duoc xu ly co ghi nhan truoc khi dung lam gold; khong sua nhan cho khop AI.
4. Khoa tap blind va muc chap nhan TRUOC khi thu model. Khong sua prompt,
   rubric, aliases hay huan luyen theo cac dap an blind da xem.
5. Chay du doan khong dua nhan giang vien vao model, sau do do rieng.

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\evaluate_backend_quality.py predict --dataset corpus.json --output predictions.json
.\.venv\Scripts\python.exe -X utf8 tools\evaluate_backend_quality.py grading --dataset corpus.json --predictions predictions.json --output grading-report.json
```

Bao cao tinh MAE, ty le chuyen xac minh, so y cho diem oan/tru diem oan,
ket qua tren nhung bai tu dong duoc chap nhan va theo tung mon/ngon ngu.
Hash transcript, rubric va diem tong phai khop tung y. Nhung diem
`unresolved` chi la can duoi tam thoi, khong duoc goi la diem da chot.

Mac dinh can it nhat 100 mau blind am thanh that co dinh danh nhom nguoi hoc
va mot tap con hai nguoi cham de duoc danh dau du du lieu XEM XET. Con so
100 chi la muc toi thieu quy trinh, khong phai chung minh thong ke hay 99%.
`eligible_for_release_review` chi danh gia ve sinh du lieu, KHONG phai
model da dat chat luong. `production_certified` luon false; cong cu khong
tu thay model, tu ha nguong hay tu bat cham tu dong. Chi so cua nhom qua
nho chua dai dien cho toan mon/ngon ngu. Du lieu synthetic, nhan assisted,
ket qua AI duoc chap nhan khong thay the gold doc lap.

## 4. STT va do tre

STT luu `timings`: cho khoa xu ly, thoi gian san sang model, giai ma tung
lan/fallback, xu ly va tong thoi gian. `model_ready_seconds` bao gom kiem
tra cache/nap model, khong phai luc nao cung la tai model tu dau.
Transcript corrector luu `correction_elapsed_seconds`; grader tra
`grading_elapsed_seconds`. Do tre cac buoc giup tach cold start, xep hang,
giai ma lan hai va sua transcript; khong danh dong voi chat luong nhan dang.
Khong tang prewarm dong loat hay them model nang cho may yeu trong ban nay.

Bao cao STT dung audio co transcript chuan do nguoi nghe xac nhan. Moi mau
co `id`, `condition` (`clean`/`noisy`), `language`, `reference`, `hypothesis`,
`critical_terms` va tuy chon `critical_spans`. Vi du critical span la ca
cum "A khong dung SQL", giup phat hien phu dinh bi chuyen sang chu the khac.
Phai lay hypothesis tu STT that, khong tu viet cho khop reference.

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\evaluate_backend_quality.py stt --dataset stt-samples.json --output stt-report.json
```

Muc tieu WER: audio sach <= 8%, co nen <= 15%, khong sai cum quan trong.
Mac dinh CLI doi ca VI va EN, moi ngon ngu du sach/nhieu. Them/doi/dao thu
tu so, mat/them phu dinh, mat/lap thuat ngu, thay doi critical spans duoc
bao rieng. Khong cho transcript chuan rong, condition sai hay cum quan trong
khong ton tai trong reference. Dem tu/so/cum KHONG phai bo chung minh ngu
nghia day du hay tach nguoi noi. Khong the suy ra WER hay % chinh xac that
truc tiep tu mic confidence khi khong co reference.

## 5. Audit nguon va gioi han con lai

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\audit_rubric_sources.py --output reports\rubric-audit-new.json
```

Cong cu chi doc hai ngan hang duoc cung cap, tao ban nhap; khong sua DB,
khong tu them synonyms tu dap an test va khong tu publish. File output cu
khong bi ghi de. Report ngay 2026-10-17 nam local trong `reports/backend_quality_20261017`,
khong di kem ban tai Git. Cac lenh tren dung moi truong runtime `.venv` da cai theo
REQUIREMENTS.md; dataset/du doan dau vao phai duoc tao rieng, khong co san chi tu lenh cai thu vien.

Van can: corpus sinh vien that duoc phep su dung; rubric V3 duoc giang vien
duyet; nhan doc lap va blind test; benchmark audio that VI/EN tren may CPU
yeu. Chua ket luan fine-tune moi, PhoWhisper, hay model lon hon tot hon khi
chua A/B tren cung du lieu. Chua the cam ket STT 99% hay chot tat ca bai
khong can giang vien. Khong dua cac tac vu export/audit vao duong chay moi
lan sinh vien tra loi.
