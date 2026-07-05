/* ============================================================
   医学知识库系统 - 前端交互脚本
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    // 侧边栏导航高亮
    var currentPath = window.location.pathname;
    document.querySelectorAll(".nav-item").forEach(function (item) {
        var href = item.getAttribute("href");
        if (href && href !== "/") {
            if (currentPath === href || currentPath === href + "/") {
                item.classList.add("active");
            }
        }
    });

    // 删除确认
    document.querySelectorAll(".btn-delete").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            if (!confirm("确认要删除该条记录吗？此操作不可撤销。")) {
                e.preventDefault();
            }
        });
    });

    // 审核驳回确认
    document.querySelectorAll(".btn-reject").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            if (!confirm("确认驳回该知识条目？")) {
                e.preventDefault();
            }
        });
    });

    // 闪现消息自动消失
    setTimeout(function () {
        document.querySelectorAll(".flash").forEach(function (el) {
            el.style.transition = "opacity 0.5s";
            el.style.opacity = "0";
            setTimeout(function () { el.remove(); }, 500);
        });
    }, 4000);

    // 搜索框回车提交
    var searchInput = document.querySelector("#searchKeyword");
    if (searchInput) {
        searchInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                document.querySelector("#searchForm").submit();
            }
        });
    }
});
