package domain

import "testing"

func TestPageResult_TotalPages(t *testing.T) {
	tests := []struct {
		name       string
		total      int32
		limit      int32
		wantPages  int32
	}{
		{"exact division", 40, 20, 2},
		{"partial page", 41, 20, 3},
		{"single page", 5, 20, 1},
		{"zero items", 0, 20, 1},
		{"zero limit", 10, 0, 1},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			p := PageResult[string]{TotalCount: tt.total, Limit: tt.limit}
			if got := p.TotalPages(); got != tt.wantPages {
				t.Errorf("TotalPages() = %d, want %d", got, tt.wantPages)
			}
		})
	}
}

func TestPageResult_CurrentPage(t *testing.T) {
	tests := []struct {
		name     string
		offset   int32
		limit    int32
		wantPage int32
	}{
		{"first page", 0, 20, 1},
		{"second page", 20, 20, 2},
		{"third page", 40, 20, 3},
		{"zero limit", 0, 0, 1},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			p := PageResult[string]{Offset: tt.offset, Limit: tt.limit}
			if got := p.CurrentPage(); got != tt.wantPage {
				t.Errorf("CurrentPage() = %d, want %d", got, tt.wantPage)
			}
		})
	}
}

func TestPageResult_HasNext(t *testing.T) {
	p := PageResult[string]{Offset: 0, Limit: 20, TotalCount: 50}
	if !p.HasNext() {
		t.Error("HasNext() should be true for first page of 50")
	}

	p = PageResult[string]{Offset: 40, Limit: 20, TotalCount: 50}
	if p.HasNext() {
		t.Error("HasNext() should be false on last page")
	}
}

func TestPageResult_HasPrev(t *testing.T) {
	p := PageResult[string]{Offset: 0, Limit: 20, TotalCount: 50}
	if p.HasPrev() {
		t.Error("HasPrev() should be false on first page")
	}

	p = PageResult[string]{Offset: 20, Limit: 20, TotalCount: 50}
	if !p.HasPrev() {
		t.Error("HasPrev() should be true on second page")
	}
}
