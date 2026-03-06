package components

import (
	"strings"
	"testing"
)

func TestPaginator_Defaults(t *testing.T) {
	p := NewPaginator(20)
	if p.Limit() != 20 {
		t.Errorf("Limit() = %d, want 20", p.Limit())
	}
	if p.Offset() != 0 {
		t.Errorf("Offset() = %d, want 0", p.Offset())
	}
	if p.Page() != 1 {
		t.Errorf("Page() = %d, want 1", p.Page())
	}
}

func TestPaginator_InvalidPerPage(t *testing.T) {
	p := NewPaginator(0)
	if p.Limit() != 20 {
		t.Errorf("zero perPage should default to 20, got %d", p.Limit())
	}
}

func TestPaginator_Navigation(t *testing.T) {
	p := NewPaginator(10).SetTotal(35)
	if p.TotalPages() != 4 {
		t.Errorf("TotalPages() = %d, want 4", p.TotalPages())
	}
	if p.HasPrev() {
		t.Error("first page should not have prev")
	}
	if !p.HasNext() {
		t.Error("first page of 4 should have next")
	}

	p = p.NextPage()
	if p.Page() != 2 {
		t.Errorf("after NextPage, Page() = %d, want 2", p.Page())
	}
	if p.Offset() != 10 {
		t.Errorf("after NextPage, Offset() = %d, want 10", p.Offset())
	}
	if !p.HasPrev() {
		t.Error("page 2 should have prev")
	}

	p = p.PrevPage()
	if p.Page() != 1 {
		t.Errorf("after PrevPage, Page() = %d, want 1", p.Page())
	}
}

func TestPaginator_ClampsOnSetTotal(t *testing.T) {
	p := NewPaginator(10).SetTotal(30)
	p = p.NextPage().NextPage() // page 3
	p = p.SetTotal(15)         // now only 2 pages
	if p.Page() > p.TotalPages() {
		t.Errorf("page %d should be clamped to totalPages %d", p.Page(), p.TotalPages())
	}
}

func TestPaginator_PrevPageAtStart(t *testing.T) {
	p := NewPaginator(10).SetTotal(30)
	p = p.PrevPage()
	if p.Page() != 1 {
		t.Error("PrevPage on first page should stay at 1")
	}
}

func TestPaginator_NextPageAtEnd(t *testing.T) {
	p := NewPaginator(10).SetTotal(20)
	p = p.NextPage() // page 2 (last)
	p = p.NextPage() // should stay
	if p.Page() != 2 {
		t.Errorf("NextPage on last page should stay, got %d", p.Page())
	}
}

func TestPaginator_View(t *testing.T) {
	p := NewPaginator(10).SetTotal(35)
	view := p.View()
	if !strings.Contains(view, "35 items") {
		t.Errorf("view should show total items, got %q", view)
	}
}

func TestPaginator_ViewEmpty(t *testing.T) {
	p := NewPaginator(10)
	view := p.View()
	if view != "" {
		t.Errorf("empty paginator should render empty, got %q", view)
	}
}
