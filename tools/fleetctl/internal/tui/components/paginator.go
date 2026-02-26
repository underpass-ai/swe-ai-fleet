package components

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Pastel pagination styles.
var (
	pageActiveStyle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // pastel periwinkle
	pageNormalStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))             // warm grey
	pageArrowActive  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("117")) // sky blue
	pageArrowDim     = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))             // dim grey
	pageTotalStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))             // warm grey
)

// Paginator wraps limit/offset pagination state and renders a page indicator.
type Paginator struct {
	perPage    int32
	page       int32 // 0-based internal
	totalItems int32
}

// NewPaginator creates a Paginator with the given items per page.
func NewPaginator(perPage int) Paginator {
	pp := int32(perPage)
	if pp <= 0 {
		pp = 20
	}
	return Paginator{perPage: pp}
}

// SetTotal updates the total item count and clamps the current page.
func (p Paginator) SetTotal(n int32) Paginator {
	p.totalItems = n
	maxPage := p.totalPages() - 1
	if maxPage < 0 {
		maxPage = 0
	}
	if p.page > maxPage {
		p.page = maxPage
	}
	return p
}

// NextPage advances to the next page if possible.
func (p Paginator) NextPage() Paginator {
	if p.page < p.totalPages()-1 {
		p.page++
	}
	return p
}

// PrevPage goes back one page if possible.
func (p Paginator) PrevPage() Paginator {
	if p.page > 0 {
		p.page--
	}
	return p
}

// Offset returns the offset for the current page.
func (p Paginator) Offset() int32 {
	return p.page * p.perPage
}

// Limit returns the page size.
func (p Paginator) Limit() int32 {
	return p.perPage
}

// Page returns the 1-based current page number.
func (p Paginator) Page() int32 {
	return p.page + 1
}

// TotalPages returns the total number of pages.
func (p Paginator) TotalPages() int32 {
	return p.totalPages()
}

// HasNext reports whether there is a next page.
func (p Paginator) HasNext() bool {
	return p.page < p.totalPages()-1
}

// HasPrev reports whether there is a previous page.
func (p Paginator) HasPrev() bool {
	return p.page > 0
}

func (p Paginator) totalPages() int32 {
	if p.perPage <= 0 || p.totalItems <= 0 {
		return 1
	}
	pages := p.totalItems / p.perPage
	if p.totalItems%p.perPage != 0 {
		pages++
	}
	return pages
}

// View renders the paginator as a styled string.
func (p Paginator) View() string {
	total := p.totalPages()
	if total <= 1 && p.totalItems <= 0 {
		return ""
	}

	var b strings.Builder

	// Left arrow
	if p.HasPrev() {
		b.WriteString(pageArrowActive.Render("<< "))
	} else {
		b.WriteString(pageArrowDim.Render("<< "))
	}

	// Page indicator: render dots for each page, highlight current
	if total <= 10 {
		for i := int32(0); i < total; i++ {
			if i == p.page {
				b.WriteString(pageActiveStyle.Render("*"))
			} else {
				b.WriteString(pageNormalStyle.Render("."))
			}
		}
	} else {
		b.WriteString(pageActiveStyle.Render(fmt.Sprintf("%d/%d", p.page+1, total)))
	}

	// Right arrow
	if p.HasNext() {
		b.WriteString(pageArrowActive.Render(" >>"))
	} else {
		b.WriteString(pageArrowDim.Render(" >>"))
	}

	// Total count
	b.WriteString(pageTotalStyle.Render(fmt.Sprintf("  %d items", p.totalItems)))

	return b.String()
}
