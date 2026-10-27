using System;
using System.Collections.Generic;
using System.Drawing;

namespace Tap2Trd {
    public class MenuElement {
        public int x { get; set; }
        public int y { get; set; }
        public int width { get; set; }
        public int ink { get; set; }
        public int paper { get; set; }
        public bool bright { get; set; }
        public bool visible { get; set; }
        public string text { get; set; }
        public MenuElement() { width = 28; ink = 7; visible = true; }
        public MenuElement Copy() { return (MenuElement)MemberwiseClone(); }
        internal Rectangle Bounds { get { return new Rectangle(x, y, width, 1); } }
    }

    public class MenuLayout {
        public const int PageSize = 16, ItemOffset = 5;
        public const string Keys = "123456789ABCDEFG";
        public int version { get; set; }
        public MenuElement title { get; set; }
        public MenuElement hint { get; set; }
        public MenuElement previous { get; set; }
        public MenuElement next { get; set; }
        public MenuElement page { get; set; }
        public List<MenuElement> items { get; set; }
        public MenuLayout() {
            version = 2; items = new List<MenuElement>();
            previous = new MenuElement { x = 2, y = 23, width = 12, ink = 6, text = "P НАЗАД" };
            next = new MenuElement { x = 18, y = 23, width = 12, ink = 6, text = "N ДАЛЕЕ" };
            page = new MenuElement { x = 2, y = 2, ink = 5, text = "СТРАНИЦА {page}/{pages}" };
        }
        public static MenuLayout Default(int count) {
            var layout = new MenuLayout {
                title = new MenuElement { x = 2, y = 1, ink = 5, bright = true },
                hint = new MenuElement { x = 2, y = 21, ink = 6, text = "НАЖМИТЕ КЛАВИШУ ИГРЫ" }
            };
            for (int i = 0; i < count; i++) layout.items.Add(new MenuElement { x = 2, y = 4 + i });
            return layout;
        }
        public MenuLayout Copy(int count) {
            var copy = new MenuLayout { title = title.Copy(), hint = hint.Copy(), version = 2,
                previous = previous.Copy(), next = next.Copy(), page = page.Copy() };
            for (int i = 0; i < count; i++) copy.items.Add(items[i].Copy());
            return copy;
        }
        public MenuElement At(int index) {
            return index == 0 ? title : index == 1 ? hint : index == 2 ? previous : index == 3 ? next : index == 4 ? page : items[index - ItemOffset];
        }
        public bool Displayed(int index, int pages) { return At(index).visible && (index < 2 || index >= ItemOffset || pages > 1); }
        public void Arrange(int count, bool twoColumns) {
            int rows = Math.Max(1, (count + 1) / 2);
            for (int i = 0; i < items.Count; i++) {
                var s = items[i];
                int column = i < 2*rows ? i/rows : (i-2*rows)/(8-rows);
                int row = i < 2*rows ? i%rows : rows+(i-2*rows)%(8-rows);
                s.x = twoColumns ? 1 + column*16 : 2; s.y = twoColumns ? 4 + row*2 : 4+i; s.width = twoColumns ? 14 : 28;
            }
        }
        public string Validate(int count, bool checkOverlap = true, int pageCount = 1) {
            if ((version != 1 && version != 2) || title == null || hint == null || previous == null || next == null || page == null ||
                items == null || count < 0 || count > PageSize || items.Count < count || items.Count > PageSize)
                return UiText.T("Неверный формат макета меню.");
            var occupied = new List<MenuElement>();
            for (int i = 0; i < count + ItemOffset; i++) {
                var s = At(i);
                string name = i == 0 ? UiText.T("Заголовок") : i == 1 ? UiText.T("Подсказка") : i == 2 ? UiText.T("Назад (P)") : i == 3 ? UiText.T("Далее (N)") : i == 4 ? UiText.T("Номер страницы") : UiText.T("Пункт ") + (i - ItemOffset + 1);
                if (s == null || s.x < 0 || s.x > 31 || s.y < 0 || s.y > 23 || s.width < (i < ItemOffset ? 1 : 4) || s.width > 32 || s.x + s.width > 32 || s.ink < 0 || s.ink > 7 || s.paper < 0 || s.paper > 7)
                    return name + UiText.T(": проверьте координаты, ширину и цвета.");
                if (i >= ItemOffset && !s.visible) return UiText.T("Пункты выбора игры нельзя скрывать.");
                if (!Displayed(i, pageCount)) continue;
                if (s.ink == s.paper) return name + UiText.T(": цвет текста совпадает с фоном.");
                foreach (var other in occupied) if (checkOverlap && other.Bounds.IntersectsWith(s.Bounds)) return name + UiText.T(" пересекается с другой надписью. Переместите или сузьте её.");
                occupied.Add(s);
            }
            return null;
        }
    }

    public class MenuTemplate {
        public int version { get; set; }
        public string title { get; set; }
        public MenuLayout layout { get; set; }
        public List<MenuLayout> pages { get; set; }
        public string background { get; set; }

        public List<MenuLayout> ReadPages() {
            List<MenuLayout> result;
            if (version == 1 && layout != null) result = new List<MenuLayout> { layout };
            else if (version == 2 && pages != null && pages.Count > 0 && pages.Count <= 128) result = pages;
            else throw new System.IO.InvalidDataException(UiText.T("Неизвестный формат макета."));
            foreach (var item in result) {
                if (item == null || item.items == null || item.items.Count != MenuLayout.PageSize)
                    throw new System.IO.InvalidDataException(UiText.T("Макет страницы должен содержать 16 позиций."));
                string error = item.Validate(MenuLayout.PageSize, false, result.Count);
                if (error != null) throw new System.IO.InvalidDataException(error);
            }
            return result;
        }
    }
}
