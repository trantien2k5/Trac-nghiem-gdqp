# Tài liệu thuật toán & mô hình dữ liệu

Tài liệu này mô tả các thuật toán và cơ chế lưu trữ dữ liệu đang dùng trong
`index.html`, để sau này có thể đóng gói lại hoặc tái sử dụng ở dự án khác mà
không cần đọc lại toàn bộ code. Tất cả state đều lưu trong `localStorage` của
trình duyệt (không có backend), theo từng học phần (`hpId`, ví dụ `hp1`, `hp2`).

## Mục lục

1. [Kho độ thuộc dùng chung (unified mastery store)](#1-kho-độ-thuộc-dùng-chung-unified-mastery-store)
2. [Thuật toán lặp lại ngắt quãng (spaced repetition) cho từng câu](#2-thuật-toán-lặp-lại-ngắt-quãng-spaced-repetition-cho-từng-câu)
3. [Luyện tập thông minh — thuật toán chọn câu (adaptive selection)](#3-luyện-tập-thông-minh--thuật-toán-chọn-câu-adaptive-selection)
4. [Cơ chế "gặp lại trong phiên" & chặn phiên phình to](#4-cơ-chế-gặp-lại-trong-phiên--chặn-phiên-phình-to)
5. [Nhật ký hoạt động & thống kê tổng quan](#5-nhật-ký-hoạt-động--thống-kê-tổng-quan)
6. [Di chuyển dữ liệu cũ (migration)](#6-di-chuyển-dữ-liệu-cũ-migration)
7. [Chế độ sáng/tối (dark mode)](#7-chế-độ-sángtối-dark-mode)
8. [Gợi ý khi tái sử dụng ở dự án khác](#8-gợi-ý-khi-tái-sử-dụng-ở-dự-án-khác)

---

## 1. Kho độ thuộc dùng chung (unified mastery store)

**Vấn đề cần giải quyết:** app có 4 chế độ học (Luyện tập, Thi thử, Ôn câu
sai, Luyện tập thông minh). Ban đầu mỗi chế độ tự lưu tiến độ riêng (ví dụ
"độ thuộc" theo từng đề khác với "độ thuộc" của chế độ thông minh), khiến học
ở chế độ này không phản ánh vào chế độ kia hay vào tab Thống kê. Giải pháp là
gộp **toàn bộ** dữ liệu độ thuộc từng câu vào **một kho duy nhất**, khoá theo
`id` câu hỏi (ổn định trong toàn học phần, không phụ thuộc câu đó nằm ở đề
nào) — mọi chế độ đọc/ghi cùng một chỗ.

**Khoá localStorage:** `quiz_<hpId>_adaptive_v1`

**Cấu trúc dữ liệu:**

```js
{
  seq: number,           // bộ đếm toàn cục, tăng dần, dùng làm "đơn vị khoảng cách"
  migratedLegacy: bool,  // đã chạy migration dữ liệu cũ chưa (xem mục 6)
  q: {
    [questionId]: {
      correctCount: number,  // tổng số lần trả lời đúng (mọi chế độ, mọi thời điểm)
      wrongCount: number,    // tổng số lần trả lời sai
      streak: number,        // số lần đúng liên tiếp ĐÃ được tính (xem mục 2)
      lastSeen: number,      // giá trị seq tại lần gần nhất câu này được trả lời (đúng hoặc sai)
      lastAdvance: number    // giá trị seq tại lần gần nhất streak thực sự thay đổi (tăng hoặc reset về 0)
    }
  }
}
```

**Vì sao tách `lastSeen` và `lastAdvance` thành 2 trường riêng:**
`lastSeen` dùng để sắp xếp "câu nào lâu chưa gặp thì ưu tiên chọn trước" khi
chọn câu cho phiên học mới — cần cập nhật ở **mọi** lần trả lời. `lastAdvance`
dùng để tính khoảng cách cho thuật toán ngắt quãng ở mục 2 — chỉ được cập
nhật khi streak **thực sự** thay đổi. Nếu dùng chung một trường, một lần trả
lời đúng nhưng "chạm hụt" (chưa đủ cách xa để tính vào streak) sẽ vô tình làm
mới luôn đồng hồ đếm khoảng cách, khiến câu đó có thể không bao giờ đạt "đã
thuộc" nếu chẳng may bị chọn lại quá sớm nhiều lần liên tiếp.

**Các hàm chính** (đều trong `index.html`):

| Hàm | Vai trò |
|---|---|
| `adaptiveKey(hpId)` | Tạo tên khoá localStorage cho học phần |
| `loadAdaptive(hpId)` | Đọc kho, trả về `{seq:0, q:{}}` nếu chưa có |
| `saveAdaptiveData(hpId, data)` | Ghi kho xuống localStorage |
| `adaptiveStatFor(data, id)` | Lấy thống kê 1 câu, trả về giá trị mặc định nếu câu chưa từng xuất hiện |
| `adaptiveGroup(stat)` | Phân loại câu thành 1 trong 4 nhóm (xem bên dưới) |
| `applyAdaptiveUpdate(hpId, id, isCorrect)` | **Hàm ghi duy nhất** — mọi chế độ đều gọi hàm này mỗi khi người dùng trả lời 1 câu lần đầu trong slot đó (xem mục 4 về khái niệm "slot") |

**Phân loại 4 nhóm** (`adaptiveGroup`):

- `new` — chưa từng trả lời (`correctCount === 0 && wrongCount === 0`)
- `wrong` — đã từng trả lời nhưng streak vừa bị reset về 0 (sai ở lần gần nhất)
- `shaky` — streak dương nhưng chưa đạt ngưỡng "đã thuộc"
- `mastered` — streak đã đạt ngưỡng `ADAPTIVE_MASTERED_STREAK`

Nhóm này vừa được dùng cho thuật toán chọn câu (mục 3), vừa được ánh xạ sang
trạng thái hiển thị (`ADAPTIVE_GROUP_TO_QSTATE`: `new→unseen`, `wrong→wrong`,
`shaky→learning`, `mastered→mastered`) dùng chung cho tab Thống kê và lưới
câu hỏi.

---

## 2. Thuật toán lặp lại ngắt quãng (spaced repetition) cho từng câu

**Tiêu chí "đã thuộc":** trả lời đúng liên tiếp đủ `ADAPTIVE_MASTERED_STREAK
= 3` lần — nhưng không phải 3 lần đúng liên tiếp **trong cùng một phiên học**
là được tính ngay, mà mỗi lần đúng chỉ được cộng vào chuỗi nếu **đã cách lần
tính streak gần nhất một khoảng đủ xa**, mô phỏng nguyên lý lặp lại ngắt
quãng kiểu Anki/SM-2 (khoảng lặp tăng dần theo độ tự tin).

```js
const ADAPTIVE_MASTERED_STREAK = 3;
const ADAPTIVE_MIN_GAP_STEPS = [0, 5, 10];
```

`ADAPTIVE_MIN_GAP_STEPS[i]` là số **câu khác** (không phải thời gian thực)
phải xen giữa để bước streak từ `i` lên `i+1` được tính:

- **0 → 1**: không cần cách (bước 0). Vừa trả lời sai xong, sửa đúng ngay lần
  sau vẫn được tính — để không phạt oan việc "vừa học vừa sửa".
- **1 → 2**: phải cách ít nhất **5 câu khác** kể từ lần tiến bước gần nhất.
- **2 → 3** (đạt "đã thuộc"): phải cách ít nhất **10 câu khác** — mốc cuối
  đòi hỏi cách xa nhất vì đây là ngưỡng quyết định câu có bị coi là nhớ thật
  hay không.

Khoảng cách được tính bằng đơn vị `seq` (bộ đếm toàn cục, tăng 1 mỗi lần
`applyAdaptiveUpdate` được gọi cho **bất kỳ** câu nào, không riêng câu đang
xét), **không** dùng thời gian thực — để không phụ thuộc người dùng học
nhanh hay chậm, mà phụ thuộc "đã ôn qua bao nhiêu câu khác" — đúng tinh thần
ngắt quãng theo mật độ luyện tập.

**Logic đầy đủ trong `applyAdaptiveUpdate`:**

```js
function applyAdaptiveUpdate(hpId, id, isCorrect){
  const data = loadAdaptive(hpId);
  const stat = adaptiveStatFor(data, id);
  const gapSinceLastAdvance = (data.seq || 0) - (stat.lastAdvance || 0); // tính TRƯỚC khi tăng seq
  data.seq = (data.seq || 0) + 1;
  if(isCorrect){
    stat.correctCount++;
    const requiredGap = ADAPTIVE_MIN_GAP_STEPS[Math.min(stat.streak, ADAPTIVE_MIN_GAP_STEPS.length - 1)];
    if(gapSinceLastAdvance >= requiredGap){
      stat.streak++;
      stat.lastAdvance = data.seq; // chỉ dời mốc khi thực sự tiến thêm 1 bước
    }
    // Nếu chưa đủ cách xa: vẫn tăng correctCount, nhưng KHÔNG tăng streak và KHÔNG dời lastAdvance.
  } else {
    stat.wrongCount++;
    stat.streak = 0;
    stat.lastAdvance = data.seq; // sai cũng là một mốc mới, tính lại khoảng cách từ đầu
  }
  stat.lastSeen = data.seq; // luôn cập nhật, phục vụ xoay vòng chọn câu
  data.q[id] = stat;
  saveAdaptiveData(hpId, data);
}
```

**Lưu ý khi cài lại thuật toán này ở nơi khác:** phải tính `gapSinceLastAdvance`
**trước** khi tăng `data.seq`, nếu tính sau sẽ bị lệch đi 1 đơn vị (tự đếm cả
lần trả lời hiện tại vào khoảng cách, làm ngưỡng thực tế thấp hơn ý định 1
bậc). Đây là lỗi off-by-one thực tế đã gặp và sửa trong quá trình phát triển.

---

## 3. Luyện tập thông minh — thuật toán chọn câu (adaptive selection)

Hàm `pickAdaptiveQuestions(hp)` chọn ra một phiên học mới, ưu tiên câu cần ôn
nhiều hơn nhưng vẫn có đủ 4 loại câu để tránh nhàm chán / học lệch.

```js
const ADAPTIVE_SESSION_SIZE = 30; // chia hết cho 40/30/20/10% -> tỉ lệ không lệch vì làm tròn
const ADAPTIVE_RATIOS = { new: 0.4, wrong: 0.3, shaky: 0.2, mastered: 0.1 };
```

**Các bước:**

1. Gộp toàn bộ câu hỏi của học phần vào 4 nhóm (`new`/`wrong`/`shaky`/`mastered`)
   theo `adaptiveGroup`.
2. Mỗi nhóm được xáo trộn ngẫu nhiên rồi sắp theo `lastSeen` tăng dần (câu
   lâu chưa xuất hiện được ưu tiên lên đầu) — vừa có yếu tố ngẫu nhiên vừa
   đảm bảo công bằng xoay vòng.
3. Tính chỉ tiêu (`quota`) mỗi nhóm = `round(target * tỉ lệ)`, phần dư do làm
   tròn được cộng bù vào nhóm `new`. Với `target = 30` thì các chỉ tiêu này
   luôn tròn số (12/9/6/3), không bao giờ lệch tỉ lệ.
4. Nếu một phiên không đủ câu để lấp đầy `target` (điển hình: nhóm `new` đã
   cạn vì đã học hết học phần), phần thiếu được bù theo thứ tự ưu tiên:
   - **Xen kẽ round-robin giữa `wrong` và `shaky`** (không rút cạn hết nhóm
     này rồi mới sang nhóm kia) — đây là điểm mấu chốt để tránh nghẽn: nếu
     rút cạn `wrong` trước, nhóm `shaky` (thường đông hơn nhiều khi đã học
     hết học phần) sẽ bị đói suất mỗi phiên, khiến "đã thuộc" tăng rất chậm
     dù người dùng luyện tập đều đặn (bug thực tế đã gặp và sửa).
   - Chỉ khi cả `wrong` và `shaky` cũng cạn (gần như toàn bộ học phần đã
     thuộc) mới lấy thêm từ `new`/`mastered`.
5. Trộn thứ tự các nhóm đã chọn theo kiểu round-robin (xen kẽ từng câu một
   nhóm) để phiên học không bị dồn cục "toàn câu mới" rồi mới đến "toàn câu
   ôn", mà rải đều.

Kết quả trả về là mảng **chỉ số câu hỏi** (index trong `hp.questions`) theo
đúng thứ tự sẽ hiển thị trong phiên.

---

## 4. Cơ chế "gặp lại trong phiên" & chặn phiên phình to

Ngoài spaced-repetition liên-phiên (mục 2), trong **một phiên** đang làm,
nếu người dùng trả lời sai một câu, câu đó được xếp lặp lại sau vài câu nữa
(không lặp lại ngay, để tránh học vẹt kiểu "vừa thấy đáp án là bấm đúng").

```js
const MAX_APPEARANCES = 4;       // 1 câu tối đa xuất hiện 4 lần / phiên
const REPEAT_GAP = 3;            // chế độ Luyện tập/Thi thử: gặp lại cách 3 câu
// Chế độ Luyện tập thông minh dùng khoảng ngẫu nhiên 5-8: 5 + Math.floor(Math.random()*4)
const SESSION_GROWTH_MULT = 1.5; // qOrder tối đa dài gấp 1.5 lần số câu chọn ban đầu
```

`scheduleRepeat(qIdx, gap)` chèn câu vào hàng đợi (`qOrder`) cách vị trí hiện
tại `gap` slot, nhưng bị chặn bởi 2 điều kiện an toàn:

- `appearCount[qIdx] >= MAX_APPEARANCES` — 1 câu không lặp lại quá 4 lần
  trong 1 phiên, tránh vòng lặp vô hạn nếu người dùng cứ trả lời sai mãi.
- `qOrder.length >= sessionQueueCap` — trần tổng số slot trong phiên
  (`sessionQueueCap = Math.ceil(initialQOrderLength * SESSION_GROWTH_MULT)`,
  tính lại mỗi khi bắt đầu phiên mới), tránh trường hợp xấu nhất phiên
  "phình to" gấp nhiều lần dự kiến ban đầu chỉ vì nhiều câu bị sai (đã kiểm
  chứng: phiên 30 câu tối đa chỉ phình tới 45, thay vì lý thuyết có thể tới
  120 nếu không chặn).

**Khái niệm "slot" quan trọng khi ghi mastery:** mỗi vị trí trong `qOrder`
là một **slot**, không phải một câu hỏi — cùng 1 câu (theo `id`) có thể xuất
hiện ở nhiều slot khác nhau trong 1 phiên (do gặp lại). `selectAnswer()` chỉ
gọi `applyAdaptiveUpdate` khi đây là **lần bấm đầu tiên trên slot đó**
(`isFirstClickOnSlot`), khác với `isFirstAttempt` (lần trả lời đầu tiên của
*câu* đó trong phiên, dùng riêng cho việc tính điểm/`logAnswer`). Nếu dùng
nhầm `isFirstAttempt` để ghi mastery, kết quả của các lần gặp-lại-để-ôn sẽ bị
bỏ qua hoàn toàn — đây là lỗi thực tế đã gặp và sửa.

---

## 5. Nhật ký hoạt động & thống kê tổng quan

**Khoá localStorage:** `quiz_activity_v1` (dùng chung toàn app, không tách
theo học phần).

```js
{
  totalAnswered, totalCorrect, totalWrong, totalTimeMs, sessionCount,
  byDate: { 'YYYY-MM-DD': { answered, correct, wrong, timeMs } },
  streakCurrent, streakBest, lastActiveDate
}
```

- `logAnswer(isCorrect)` — gọi khi trả lời lần đầu 1 câu trong phiên
  (`isFirstAttempt`), cộng dồn số liệu ngày hiện tại + gọi `touchStreak`.
- `logSessionTime(ms)` — gọi khi kết thúc phiên (`finishQuiz`) **và** khi
  thoát giữa chừng đã xác nhận, để thời gian học không bị mất khi thoát sớm.
- `touchStreak(a, today)` — nếu hôm nay chưa tính, so `lastActiveDate` với
  hôm qua: liền mạch thì `streakCurrent + 1`, gãy mạch thì reset về 1.
- `liveStreak(a)` — giá trị **hiển thị**: nếu lần hoạt động gần nhất không
  phải hôm nay hoặc hôm qua (bỏ lỡ ≥ 2 ngày) thì hiển thị 0, dù số liệu gốc
  trong storage vẫn giữ nguyên để lần trả lời tiếp theo tính tiếp đúng logic
  `touchStreak`.

`computeHpStats(hp)` gộp dữ liệu điểm theo đề (`quiz_<hp>_results_v1`, vẫn
giữ để lưu điểm cao nhất từng đề) với trạng thái độ thuộc từng câu (đọc từ
kho ở mục 1 qua `questionState`/`adaptiveStatFor`) để ra số liệu theo học
phần: `masteredCount`, `learningCount`, `wrongCount`, `masteredPct`, `avgPct`
(điểm trung bình các đề đã làm), `bestPct`.

`computeGlobalStats()` gộp `computeHpStats` của mọi học phần trong `HP_LIST`
với nhật ký hoạt động, phục vụ 5 thẻ tổng quan trong tab Thống kê (Hiệu
suất, Hôm nay, Chuỗi học, Câu cần ôn, Tiến độ theo học phần) và 6 thẻ nhanh ở
màn hình chính.

**Lưu ý về sự khác biệt nhỏ có chủ đích:** "Độ chính xác" ở thẻ trang chủ
(`avgPct`, trung bình điểm cao nhất từng đề) và "Độ chính xác" ở tab Thống
kê (`accuracyPct = totalCorrect/totalAnswered` thực tế toàn bộ) là **hai
công thức khác nhau**, cùng tên nhưng ý nghĩa hơi khác — nếu tái sử dụng nên
đặt tên rõ ràng hơn để tránh nhầm lẫn.

---

## 6. Di chuyển dữ liệu cũ (migration)

Trước khi có kho chung (mục 1), độ thuộc được lưu riêng theo từng đề trong
`quiz_<hp>_results_v1` (thang streak 0-3, khoá theo **chỉ số cục bộ trong
đề**, không phải `id` câu). `migrateLegacyMasteryIfNeeded(hp)` chuyển dữ liệu
này sang kho chung **một lần duy nhất**:

- Đánh dấu bằng cờ `data.migratedLegacy` — chỉ chạy khi cờ chưa bật.
- Với mỗi câu có dữ liệu cũ: nếu câu đó **đã có** dữ liệu trong kho chung thì
  bỏ qua (không đè lên dữ liệu mới hơn).
- `oldStreak` (0-3) được giữ nguyên giá trị khi gán vào `streak` mới, vì
  ngưỡng "đã thuộc" cũ (streak ≥ 3) và mới (`ADAPTIVE_MASTERED_STREAK = 3`)
  trùng nhau — không cần quy đổi thang điểm.
- Hàm này **idempotent** và được gọi phòng thủ ở mọi nơi đọc kho chung (chọn
  câu, tính thống kê, thu thập câu sai, hiển thị %...), không chỉ ở lúc vào
  màn hình chính, để tránh trường hợp đọc dữ liệu trước khi migrate lỡ chạy.

---

## 7. Chế độ sáng/tối (dark mode)

- Bảng màu định nghĩa bằng CSS custom properties trên `:root` (sáng) và
  `:root[data-theme="dark"]` (tối) — toàn bộ UI dùng biến (`var(--...)`),
  không hardcode màu, để đổi theme không cần đổi logic JS.
- `applyTheme(theme)` set thuộc tính `data-theme` trên `<html>`, đổi icon nút
  bật/tắt (🌙/☀️), đổi `<meta name="theme-color">` (màu thanh trạng thái
  trình duyệt di động), và lưu lựa chọn vào `localStorage['theme_pref']`.
- **Chống nháy sai theme khi tải trang (flash of wrong theme):** một đoạn
  `<script>` đồng bộ được đặt ngay sau `</style>` trong `<head>` (chạy trước
  khi `<body>` render), đọc `theme_pref` đã lưu, nếu chưa có thì dùng
  `prefers-color-scheme: dark` của hệ thống làm mặc định, rồi set
  `data-theme` ngay lập tức — tránh việc trang hiện sáng rồi mới chớp sang
  tối (hoặc ngược lại) sau khi JS chính load xong.
- Nút chuyển theme (`#theme-toggle`) bị ẩn khi đang ở màn hình làm bài để
  không đè lên thanh trên cùng (đồng hồ đếm giờ, lưới câu hỏi).

---

## 8. Gợi ý khi tái sử dụng ở dự án khác

Nếu muốn đóng gói các thuật toán trên (tách khỏi câu hỏi GDQP cụ thể) để
dùng cho một bộ câu hỏi trắc nghiệm khác:

- **Bắt buộc giữ nguyên bất biến (invariant)** khi ghi dữ liệu: gọi
  `applyAdaptiveUpdate` đúng **một lần cho mỗi lần người học thực sự chọn
  đáp án lần đầu trên một slot hiển thị** — gọi thiếu (bỏ sót lần gặp lại)
  hoặc gọi thừa (đổi đáp án trong chế độ thi thử tính thêm 1 lần) đều làm sai
  lệch toàn bộ streak/gap.
- Có thể tách 3 phần độc lập nếu chỉ cần một phần:
  - **Lõi lưu trữ + gap logic** (mục 1-2): hoàn toàn không phụ thuộc cấu
    trúc câu hỏi, chỉ cần một `id` ổn định cho mỗi câu.
  - **Thuật toán chọn câu** (mục 3): cần danh sách toàn bộ câu hỏi + kho ở
    trên, không phụ thuộc UI.
  - **Nhật ký hoạt động** (mục 5): hoàn toàn độc lập, có thể dùng cho bất kỳ
    app luyện tập nào cần "chuỗi ngày học" kiểu Duolingo.
- Các hằng số (`ADAPTIVE_MASTERED_STREAK`, `ADAPTIVE_MIN_GAP_STEPS`,
  `ADAPTIVE_SESSION_SIZE`, `ADAPTIVE_RATIOS`, `MAX_APPEARANCES`,
  `REPEAT_GAP`, `SESSION_GROWTH_MULT`) đều được đặt tập trung, có thể chỉnh
  theo độ khó/độ dài bộ câu hỏi mới mà không cần sửa logic.
- Toàn bộ state chỉ ở `localStorage`, không có backend/đồng bộ nhiều thiết
  bị — nếu cần đồng bộ, đây là điểm cần thêm lớp lưu trữ mới (ví dụ sync lên
  server), giữ nguyên phần logic tính toán.
